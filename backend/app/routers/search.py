from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.db import get_db
from backend.app.models import Client, Job, Note, User
from backend.app.deps import get_current_user

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/clients")
def search_clients(q: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	items = (
		db.query(Client)
		.filter(Client.owner_id == current_user.id)
		.filter((Client.name.ilike(f"%{q}%")) | (Client.phone.ilike(f"%{q}%")))
		.order_by(Client.created_at.desc())
		.limit(50)
		.all()
	)
	return items


@router.get("/jobs")
def search_jobs(q: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	items = (
		db.query(Job)
		.filter(Job.owner_id == current_user.id)
		.filter((Job.site.ilike(f"%{q}%")) | (Job.status.ilike(f"%{q}%")))
		.order_by(Job.created_at.desc())
		.limit(50)
		.all()
	)
	return items


@router.get("/notes")
def search_notes(q: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	items = (
		db.query(Note)
		.filter(Note.owner_id == current_user.id)
		.filter((Note.text.ilike(f"%{q}%")) | (Note.status.ilike(f"%{q}%")))
		.order_by(Note.created_at.desc())
		.limit(50)
		.all()
	)
	return items
