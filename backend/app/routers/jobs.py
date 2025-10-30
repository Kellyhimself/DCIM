from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.app.db import get_db
from backend.app.models import Job, Client, User
from backend.app.schemas import JobCreate, JobOut
from backend.app.deps import get_current_user
from backend.app.pdf import generate_job_pdf
from backend.app.storage import get_s3_client
from backend.app.settings import settings

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
	pdf_bytes = generate_job_pdf(company_name=current_user.full_name or "Job Card", client_name=client_name, site=j.site, job_id=str(j.id), items=[])
	key = f"users/{current_user.id}/jobs/{j.id}/job-card.pdf"
	s3 = get_s3_client()
	s3.put_object(Bucket=settings.s3_bucket, Key=key, Body=pdf_bytes, ContentType="application/pdf")
	url = s3.generate_presigned_url("get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=3600)
	return {"key": key, "url": url}
