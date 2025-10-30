from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
import redis
import uuid
from datetime import datetime

from backend.app.db import get_db
from backend.app.models import Note, Media, User, Client, Job
from backend.app.schemas import NoteCreate, NoteOut, PresignResponse, NoteAssignRequest, NoteStatusRequest, ShareSummaryResponse
from backend.app.deps import get_current_user
from backend.app.storage import create_presigned_put
from backend.app.settings import settings

router = APIRouter(prefix="/notes", tags=["notes"])


def get_redis():
	return redis.from_url(settings.redis_url)


@router.post("", response_model=NoteOut)
def create_note(payload: NoteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	n = Note(owner_id=current_user.id)
	# link client/job if provided
	if payload.client_id:
		try:
			cid = UUID(payload.client_id)
		except Exception:
			raise HTTPException(status_code=400, detail="Invalid client_id")
		c = db.query(Client).filter(Client.id == cid, Client.owner_id == current_user.id).first()
		if not c:
			raise HTTPException(status_code=400, detail="Client not found")
		n.client_id = cid
	if payload.job_id:
		try:
			jid = UUID(payload.job_id)
		except Exception:
			raise HTTPException(status_code=400, detail="Invalid job_id")
		j = db.query(Job).filter(Job.id == jid, Job.owner_id == current_user.id).first()
		if not j:
			raise HTTPException(status_code=400, detail="Job not found")
		n.job_id = jid
	if payload.text:
		n.text = payload.text

	db.add(n)
	db.commit()
	db.refresh(n)

	# optionally prepare a media record and presigned URL
	if payload.media_type in ("audio", "photo"):
		m = Media(note_id=n.id, type=payload.media_type, key="", content_type=payload.content_type or None, uploaded=False)
		db.add(m)
		db.commit()
		db.refresh(m)
		key = f"users/{current_user.id}/notes/{n.id}/{payload.media_type}-{m.id}-{uuid.uuid4().hex}"
		m.key = key
		db.commit()
		upload_url, headers = create_presigned_put(key, payload.content_type)
		return NoteOut.model_validate({
			"id": n.id,
			"client_id": n.client_id,
			"job_id": n.job_id,
			"assignee_id": n.assignee_id,
			"text": n.text,
			"status": n.status,
			"media": [{
				"id": m.id,
				"type": m.type,
				"key": m.key,
				"content_type": m.content_type,
				"uploaded": m.uploaded,
			}],
		})

	return n  # FastAPI will serialize via from_attributes


@router.post("/{note_id}/presign", response_model=PresignResponse)
def presign_upload(note_id: UUID, kind: str, content_type: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	n = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
	if not n:
		raise HTTPException(status_code=404, detail="Not found")
	if kind not in ("audio", "photo"):
		raise HTTPException(status_code=400, detail="Invalid kind")
	m = Media(note_id=n.id, type=kind, key="", content_type=content_type or None, uploaded=False)
	db.add(m)
	db.commit()
	db.refresh(m)
	key = f"users/{current_user.id}/notes/{n.id}/{kind}-{m.id}-{uuid.uuid4().hex}"
	m.key = key
	db.commit()
	upload_url, headers = create_presigned_put(m.key, content_type)
	return PresignResponse(upload_url=upload_url, headers=headers, key=m.key, media_id=m.id)


@router.post("/{note_id}/finalize")
def finalize_upload(note_id: UUID, media_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	m = db.query(Media).join(Note, Media.note_id == Note.id).filter(Media.id == media_id, Note.id == note_id, Note.owner_id == current_user.id).first()
	if not m:
		raise HTTPException(status_code=404, detail="Not found")
	m.uploaded = True
	# if audio, enqueue STT job
	if m.type == "audio":
		r = get_redis()
		job = {"note_id": str(note_id), "media_id": str(media_id), "key": m.key, "owner_id": str(current_user.id)}
		r.lpush("stt_jobs", json.dumps(job))
	db.commit()
	return {"ok": True}


@router.get("", response_model=List[NoteOut])
def list_notes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	notes = db.query(Note).filter(Note.owner_id == current_user.id).order_by(Note.created_at.desc()).all()
	return notes


@router.post("/{note_id}/assign", response_model=NoteOut)
def assign_note(note_id: UUID, payload: NoteAssignRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	n = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
	if not n:
		raise HTTPException(status_code=404, detail="Not found")
	if payload.assignee_id:
		try:
			aid = UUID(payload.assignee_id)
		except Exception:
			raise HTTPException(status_code=400, detail="Invalid assignee_id")
		assignee = db.query(User).filter(User.id == aid).first()
		if not assignee:
			raise HTTPException(status_code=400, detail="Assignee not found")
		n.assignee_id = aid
	else:
		n.assignee_id = None
	db.commit()
	db.refresh(n)
	return n


@router.post("/{note_id}/status", response_model=NoteOut)
def update_status(note_id: UUID, payload: NoteStatusRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	n = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
	if not n:
		raise HTTPException(status_code=404, detail="Not found")
	if payload.status not in ("pending", "done"):
		raise HTTPException(status_code=400, detail="Invalid status")
	n.status = payload.status
	db.commit()
	db.refresh(n)
	return n


@router.post("/{note_id}/share_summary", response_model=ShareSummaryResponse)
def share_summary(note_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	n = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
	if not n:
		raise HTTPException(status_code=404, detail="Not found")
	client: Optional[Client] = db.query(Client).filter(Client.id == n.client_id).first() if n.client_id else None
	job: Optional[Job] = db.query(Job).filter(Job.id == n.job_id).first() if n.job_id else None
	media_count = db.query(Media).filter(Media.note_id == n.id, Media.uploaded == True).count()  # noqa: E712
	lines = []
	if client:
		lines.append(f"Client: {client.name}{' (' + client.phone + ')' if client.phone else ''}")
	if job and job.site:
		lines.append(f"Site: {job.site}")
	lines.append(f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}")
	if n.text:
		lines.append("")
		lines.append(n.text.strip())
	if media_count:
		lines.append("")
		lines.append(f"Attachments: {media_count}")
	lines.append("")
	lines.append("Thanks,")
	lines.append(current_user.full_name or "Team")
	return ShareSummaryResponse(text="\n".join(lines))
