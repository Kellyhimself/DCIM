from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Set
from uuid import UUID

from backend.app.db import get_db
from backend.app.models import Job, Client, User, Note
from backend.app.schemas import JobCreate, JobOut
from backend.app.deps import get_current_user
from backend.app.pdf import generate_job_pdf
from backend.app.storage import get_s3_client, create_presigned_get
from backend.app.settings import settings
from backend.app.routers.nlp import _extract_phones, _extract_amounts, _extract_dates, _extract_parts

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut)
def create_job(payload: JobCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	try:
		client_uuid = UUID(payload.client_id)
	except Exception:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")
	client = db.query(Client).filter(Client.id == client_uuid, Client.owner_id == current_user.id).first()
	if not client:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client not found")
	j = Job(owner_id=current_user.id, client_id=client_uuid, site=payload.site, status=payload.status or "open")
	db.add(j)
	db.commit()
	db.refresh(j)
	return j


@router.get("", response_model=List[JobOut])
def list_jobs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	return db.query(Job).filter(Job.owner_id == current_user.id).order_by(Job.created_at.desc()).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	j = db.query(Job).filter(Job.id == job_id, Job.owner_id == current_user.id).first()
	if not j:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	return j


@router.put("/{job_id}", response_model=JobOut)
def update_job(job_id: UUID, payload: JobCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	j = db.query(Job).filter(Job.id == job_id, Job.owner_id == current_user.id).first()
	if not j:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	try:
		client_uuid = UUID(payload.client_id)
	except Exception:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")
	client = db.query(Client).filter(Client.id == client_uuid, Client.owner_id == current_user.id).first()
	if not client:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client not found")
	j.client_id = client_uuid
	j.site = payload.site
	j.status = payload.status or j.status
	db.commit()
	db.refresh(j)
	return j


@router.delete("/{job_id}")
def delete_job(job_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	j = db.query(Job).filter(Job.id == job_id, Job.owner_id == current_user.id).first()
	if not j:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	db.delete(j)
	db.commit()
	return {"ok": True}


@router.post("/{job_id}/pdf")
def generate_job_pdf_route(job_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	j = db.query(Job).filter(Job.id == job_id, Job.owner_id == current_user.id).first()
	if not j:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	client = db.query(Client).filter(Client.id == j.client_id, Client.owner_id == current_user.id).first()
	client_name = client.name if client else "-"
	
	# Fetch all notes for this job
	notes = db.query(Note).filter(Note.job_id == job_id, Note.owner_id == current_user.id).order_by(Note.created_at.asc()).all()
	
	# Prepare notes data and extract entities from all notes
	notes_data = []
	all_parts: Set[str] = set()#in python, a set is a collection of unique items, so if we have duplicate items, the set will only keep one of them
	all_amounts: Set[str] = set()
	all_dates: Set[str] = set()
	all_phones: Set[str] = set()
	
	for note in notes:
		if note.text:
			notes_data.append({
				"text": note.text,
				"created_at": note.created_at.isoformat() if note.created_at else None
			})
			# Extract entities from each note
			parts = _extract_parts(note.text)
			amounts = _extract_amounts(note.text)
			dates = _extract_dates(note.text)
			phones = _extract_phones(note.text, "KE")
			
			all_parts.update(parts)
			all_amounts.update(amounts)
			all_dates.update(dates)
			all_phones.update(phones)
	
	pdf_bytes = generate_job_pdf(
		company_name=current_user.full_name or "Job Card",
		client_name=client_name,
		site=j.site,
		job_id=str(j.id),
		items=[],
		notes=notes_data if notes_data else None,
		parts=list(all_parts) if all_parts else None,
		amounts=list(all_amounts) if all_amounts else None,
		dates=list(all_dates) if all_dates else None,
		phones=list(all_phones) if all_phones else None
	)
	key = f"users/{current_user.id}/jobs/{j.id}/job-card.pdf"
	s3 = get_s3_client()
	s3.put_object(Bucket=settings.s3_bucket, Key=key, Body=pdf_bytes, ContentType="application/pdf")
	# Return direct download URL through backend API instead of presigned URL
	return {"key": key, "url": f"/jobs/{job_id}/pdf/download"}


@router.get("/{job_id}/pdf/download")
def download_job_pdf(job_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	"""Download PDF directly from backend (proxied from S3)."""
	j = db.query(Job).filter(Job.id == job_id, Job.owner_id == current_user.id).first()
	if not j:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	
	key = f"users/{current_user.id}/jobs/{j.id}/job-card.pdf"
	s3 = get_s3_client()
	
	try:
		# Download PDF from S3
		response = s3.get_object(Bucket=settings.s3_bucket, Key=key)
		pdf_bytes = response['Body'].read()
		
		# Return PDF as response
		return Response(
			content=pdf_bytes,
			media_type="application/pdf",
			headers={
				"Content-Disposition": f'attachment; filename="job-card-{job_id}.pdf"',
			}
		)
	except Exception as e:
		error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
		if error_code == 'NoSuchKey':
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found. Please generate it first.")
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to download PDF: {str(e)}")
