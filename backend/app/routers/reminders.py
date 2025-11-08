from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
import logging

from backend.app.deps import get_db, get_current_user
from backend.app.models import User, Reminder, Note, Job, Client
from backend.app.routers.nlp import extract_entities
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reminders", tags=["reminders"])


class ReminderCreate(BaseModel):
	text: str
	type: str = "follow_up"  # follow_up, call, return, check, meeting
	due_date_text: Optional[str] = None  # e.g., "Monday", "tomorrow"
	due_date: Optional[datetime] = None  # Parsed datetime
	note_id: Optional[UUID] = None
	job_id: Optional[UUID] = None
	client_id: Optional[UUID] = None


class ReminderUpdate(BaseModel):
	text: Optional[str] = None
	type: Optional[str] = None
	due_date: Optional[datetime] = None
	status: Optional[str] = None  # pending, completed, cancelled


class ReminderResponse(BaseModel):
	id: UUID
	text: str
	type: str
	due_date: Optional[datetime]
	due_date_text: Optional[str]
	status: str
	note_id: Optional[UUID]
	job_id: Optional[UUID]
	client_id: Optional[UUID]
	created_at: datetime
	updated_at: datetime
	completed_at: Optional[datetime]

	class Config:
		from_attributes = True


@router.get("", response_model=List[ReminderResponse])
def list_reminders(
	status: Optional[str] = Query(None, description="Filter by status (pending, completed, cancelled)"),
	type: Optional[str] = Query(None, description="Filter by type"),
	due_before: Optional[str] = Query(None, description="Filter reminders due before date (YYYY-MM-DD)"),
	limit: int = Query(50, ge=1, le=100),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""List reminders for the current user."""
	query = db.query(Reminder).filter(Reminder.owner_id == current_user.id)
	
	if status:
		query = query.filter(Reminder.status == status)
	if type:
		query = query.filter(Reminder.type == type)
	if due_before:
		try:
			due_date = datetime.strptime(due_before, "%Y-%m-%d").date()
			query = query.filter(Reminder.due_date <= datetime.combine(due_date, datetime.max.time()))
		except ValueError:
			pass
	
	reminders = query.order_by(Reminder.due_date.asc().nulls_last(), Reminder.created_at.desc()).limit(limit).all()
	return reminders


@router.post("", response_model=ReminderResponse, status_code=201)
def create_reminder(
	payload: ReminderCreate,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Create a new reminder."""
	# Validate related entities belong to user
	if payload.note_id:
		note = db.query(Note).filter(Note.id == payload.note_id, Note.owner_id == current_user.id).first()
		if not note:
			raise HTTPException(status_code=404, detail="Note not found")
	
	if payload.job_id:
		job = db.query(Job).filter(Job.id == payload.job_id, Job.owner_id == current_user.id).first()
		if not job:
			raise HTTPException(status_code=404, detail="Job not found")
	
	if payload.client_id:
		client = db.query(Client).filter(Client.id == payload.client_id, Client.owner_id == current_user.id).first()
		if not client:
			raise HTTPException(status_code=404, detail="Client not found")
	
	reminder = Reminder(
		owner_id=current_user.id,
		text=payload.text,
		type=payload.type,
		due_date=payload.due_date,
		due_date_text=payload.due_date_text,
		note_id=payload.note_id,
		job_id=payload.job_id,
		client_id=payload.client_id,
		status="pending"
	)
	
	db.add(reminder)
	db.commit()
	db.refresh(reminder)
	
	logger.info(f"Created reminder {reminder.id} for user {current_user.id}")
	return reminder


@router.post("/extract-from-note/{note_id}", response_model=List[ReminderResponse])
def extract_reminders_from_note(
	note_id: UUID,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Extract reminders from a note using NLP and create them."""
	note = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
	if not note:
		raise HTTPException(status_code=404, detail="Note not found")
	
	if not note.text:
		return []
	
	# Extract entities using NLP
	entities = extract_entities(note.text, "KE")
	
	created_reminders = []
	
	# Create reminders from extracted reminder intents
	for reminder_data in entities.reminders:
		if not isinstance(reminder_data, dict):
			continue
		
		text = reminder_data.get("text", "")
		due_date_text = reminder_data.get("due_date", "")
		reminder_type = reminder_data.get("type", "follow_up")
		
		if not text:
			continue
		
		# Try to parse due_date_text to datetime (simplified - could use dateutil)
		due_date = None
		try:
			# Simple parsing for common patterns
			due_date_text_lower = due_date_text.lower()
			now = datetime.now()
			
			if "tomorrow" in due_date_text_lower:
				due_date = now + timedelta(days=1)
			elif "today" in due_date_text_lower:
				due_date = now
			elif "monday" in due_date_text_lower:
				days_ahead = (0 - now.weekday()) % 7
				if days_ahead == 0:  # Today is Monday
					days_ahead = 7
				due_date = now + timedelta(days=days_ahead)
			# Add more date parsing as needed
		except Exception as e:
			logger.warning(f"Could not parse due date '{due_date_text}': {e}")
		
		reminder = Reminder(
			owner_id=current_user.id,
			note_id=note.id,
			job_id=note.job_id,
			client_id=note.client_id,
			text=text,
			type=reminder_type,
			due_date=due_date,
			due_date_text=due_date_text,
			status="pending"
		)
		
		db.add(reminder)
		created_reminders.append(reminder)
	
	if created_reminders:
		db.commit()
		for r in created_reminders:
			db.refresh(r)
		logger.info(f"Created {len(created_reminders)} reminders from note {note_id}")
	
	return created_reminders


@router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(
	reminder_id: UUID,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Get a specific reminder."""
	reminder = db.query(Reminder).filter(
		Reminder.id == reminder_id,
		Reminder.owner_id == current_user.id
	).first()
	
	if not reminder:
		raise HTTPException(status_code=404, detail="Reminder not found")
	
	return reminder


@router.put("/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
	reminder_id: UUID,
	payload: ReminderUpdate,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Update a reminder."""
	reminder = db.query(Reminder).filter(
		Reminder.id == reminder_id,
		Reminder.owner_id == current_user.id
	).first()
	
	if not reminder:
		raise HTTPException(status_code=404, detail="Reminder not found")
	
	if payload.text is not None:
		reminder.text = payload.text
	if payload.type is not None:
		reminder.type = payload.type
	if payload.due_date is not None:
		reminder.due_date = payload.due_date
	if payload.status is not None:
		reminder.status = payload.status
		if payload.status == "completed" and not reminder.completed_at:
			reminder.completed_at = datetime.utcnow()
		elif payload.status != "completed":
			reminder.completed_at = None
	
	db.commit()
	db.refresh(reminder)
	
	return reminder


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(
	reminder_id: UUID,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Delete a reminder."""
	reminder = db.query(Reminder).filter(
		Reminder.id == reminder_id,
		Reminder.owner_id == current_user.id
	).first()
	
	if not reminder:
		raise HTTPException(status_code=404, detail="Reminder not found")
	
	db.delete(reminder)
	db.commit()
	
	return None

