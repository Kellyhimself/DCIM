from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from backend.app.db import get_db
from backend.app.models import Client, Job, Note, User
from backend.app.deps import get_current_user

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/clients")
def search_clients(
	q: Optional[str] = Query(None, description="Search query for name or phone"),
	phone: Optional[str] = Query(None, description="Filter by exact phone number"),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	query = db.query(Client).filter(Client.owner_id == current_user.id)
	
	if q:
		query = query.filter((Client.name.ilike(f"%{q}%")) | (Client.phone.ilike(f"%{q}%")))
	
	if phone:
		query = query.filter(Client.phone.ilike(f"%{phone}%"))
	
	items = query.order_by(Client.created_at.desc()).limit(50).all()
	return items


@router.get("/jobs")
def search_jobs(
	q: Optional[str] = Query(None, description="Search query for site or status"),
	job_type: Optional[str] = Query(None, description="Filter by job type (plumbing, electrical, carpentry, etc.)"),
	location: Optional[str] = Query(None, description="Filter by location/site"),
	status: Optional[str] = Query(None, description="Filter by job status (open, closed)"),
	start_date: Optional[str] = Query(None, description="Filter jobs created after this date (YYYY-MM-DD)"),
	end_date: Optional[str] = Query(None, description="Filter jobs created before this date (YYYY-MM-DD)"),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	query = db.query(Job).filter(Job.owner_id == current_user.id)
	
	if q:
		query = query.filter((Job.site.ilike(f"%{q}%")) | (Job.status.ilike(f"%{q}%")))
	
	if location:
		query = query.filter(Job.site.ilike(f"%{location}%"))
	
	if status:
		query = query.filter(Job.status == status.lower())
	
	if start_date:
		try:
			start = datetime.strptime(start_date, "%Y-%m-%d").date()
			query = query.filter(Job.created_at >= datetime.combine(start, datetime.min.time()))
		except ValueError:
			pass
	
	if end_date:
		try:
			end = datetime.strptime(end_date, "%Y-%m-%d").date()
			query = query.filter(Job.created_at <= datetime.combine(end, datetime.max.time()))
		except ValueError:
			pass
	
	# Filter by job type: search in linked notes' text
	if job_type:
		query = query.join(Note, Job.id == Note.job_id).filter(Note.text.ilike(f"%{job_type}%")).distinct()
	
	items = query.order_by(Job.created_at.desc()).limit(50).all()
	return items


@router.get("/notes")
def search_notes(
	q: Optional[str] = Query(None, description="Search query for note text or status"),
	part: Optional[str] = Query(None, description="Filter by part name mentioned in note"),
	phone: Optional[str] = Query(None, description="Filter by phone number mentioned in note"),
	job_type: Optional[str] = Query(None, description="Filter by job type mentioned in note"),
	location: Optional[str] = Query(None, description="Filter by location mentioned in note"),
	start_date: Optional[str] = Query(None, description="Filter notes created after this date (YYYY-MM-DD)"),
	end_date: Optional[str] = Query(None, description="Filter notes created before this date (YYYY-MM-DD)"),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	query = db.query(Note).filter(Note.owner_id == current_user.id)
	
	if q:
		query = query.filter((Note.text.ilike(f"%{q}%")) | (Note.status.ilike(f"%{q}%")))
	
	if part:
		query = query.filter(Note.text.ilike(f"%{part}%"))
	
	if phone:
		query = query.filter(Note.text.ilike(f"%{phone}%"))
	
	if job_type:
		query = query.filter(Note.text.ilike(f"%{job_type}%"))
	
	if location:
		query = query.filter(Note.text.ilike(f"%{location}%"))
	
	if start_date:
		try:
			start = datetime.strptime(start_date, "%Y-%m-%d").date()
			query = query.filter(Note.created_at >= datetime.combine(start, datetime.min.time()))
		except ValueError:
			pass
	
	if end_date:
		try:
			end = datetime.strptime(end_date, "%Y-%m-%d").date()
			query = query.filter(Note.created_at <= datetime.combine(end, datetime.max.time()))
		except ValueError:
			pass
	
	items = query.order_by(Note.created_at.desc()).limit(50).all()
	return items
