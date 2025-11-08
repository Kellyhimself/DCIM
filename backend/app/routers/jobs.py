from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Set
from uuid import UUID
import logging

from backend.app.db import get_db
from backend.app.models import Job, Client, User, Note
from backend.app.schemas import JobCreate, JobOut
from backend.app.deps import get_current_user
from backend.app.pdf import generate_job_pdf
from backend.app.storage import get_s3_client, create_presigned_get
from backend.app.settings import settings
from backend.app.routers.nlp import _extract_phones, _extract_amounts, _extract_dates, _extract_parts, extract_entities

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


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


@router.delete("/all", status_code=status.HTTP_200_OK)
def delete_all_jobs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	"""
	Delete all jobs for the current user.
	This will cascade delete associated notes and their media files.
	Reminders linked to these jobs will have their job_id set to NULL.
	"""
	jobs = db.query(Job).filter(Job.owner_id == current_user.id).all()
	count = len(jobs)
	
	for job in jobs:
		db.delete(job)
	
	db.commit()
	logger.info(f"Deleted {count} jobs for user {current_user.id}")
	
	return {
		"message": f"Deleted {count} jobs",
		"count": count
	}


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


def extract_amount_value(amount_str: str) -> float:
	"""Extract numeric value from amount string like '5000 Kenyan shillings' or '2000'."""
	import re
	# Remove common currency words
	cleaned = re.sub(r'(kenyan\s+)?shillings?|kes|ksh', '', amount_str.lower(), flags=re.IGNORECASE)
	# Remove commas and extract numbers
	numbers = re.findall(r'[\d,]+\.?\d*', cleaned)
	if numbers:
		# Remove commas and convert to float
		value_str = numbers[0].replace(',', '')
		try:
			return float(value_str)
		except ValueError:
			pass
	return 0.0


@router.get("/{job_id}/financial")
def get_job_financial(
	job_id: UUID,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""
	Get financial summary for a specific job.
	Extracts financial data from notes linked to this job using NLP.
	"""
	j = db.query(Job).filter(Job.id == job_id, Job.owner_id == current_user.id).first()
	if not j:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
	
	# Get all notes for this job
	notes = db.query(Note).filter(
		Note.job_id == job_id,
		Note.owner_id == current_user.id,
		Note.text.isnot(None)
	).all()
	
	total_earnings = 0.0
	total_expenses = 0.0
	total_projected_earnings = 0.0
	total_projected_expenses = 0.0
	
	# Process each note
	for note in notes:
		if not note.text:
			continue
		
		# Extract entities using NLP (will use cache if available)
		entities = extract_entities(note.text, "KE")
		
		# Track processed amounts to avoid double-counting
		processed_amounts = set()
		
		# Process ACTUAL earnings
		for earning_str in entities.earnings:
			amount = extract_amount_value(earning_str)
			total_earnings += amount
			processed_amounts.add(amount)
		
		# Process ACTUAL expenses
		for expense_str in entities.expenses:
			amount = extract_amount_value(expense_str)
			total_expenses += amount
			processed_amounts.add(amount)
		
		# Process PROJECTED expenses FIRST (planned costs, estimates)
		# Filter out labor charges that LLM incorrectly categorized as expenses
		note_projected_expenses = 0.0
		labor_charges_from_expenses = []  # Track labor charges that were misclassified
		for expense_str in entities.projected_expenses:
			expense_lower = expense_str.lower()
			# Check if this is actually a labor charge (common LLM mistake)
			if any(phrase in expense_lower for phrase in ["labor charges", "labour charges", "labor fees", "labour fees", "charges will be", "charges are"]):
				# This is a labor charge, not an expense - move it to earnings
				amount = extract_amount_value(expense_str)
				labor_charges_from_expenses.append(amount)
				processed_amounts.add(amount)
			else:
				# This is a legitimate projected expense
				amount = extract_amount_value(expense_str)
				total_projected_expenses += amount
				note_projected_expenses += amount
				processed_amounts.add(amount)
		
		# Fallback: Process uncategorized amounts to capture expenses that LLM missed
		# This MUST run BEFORE calculating earnings from total quote
		# First, identify total quote and labor charges amounts to exclude them from fallback processing
		pre_identified_total_quote = None
		pre_identified_labor_charges = None
		for earning_str in entities.projected_earnings:
			earning_lower = earning_str.lower()
			amount = extract_amount_value(earning_str)
			if any(phrase in earning_lower for phrase in ["total quote", "quote is", "quote to", "total will be", "revised quote", "updated quote", "total pot", "total cut"]):
				pre_identified_total_quote = amount
			elif any(phrase in earning_lower for phrase in ["labor charges", "labour charges", "labor fees", "labour fees", "charges will be", "charges are"]):
				pre_identified_labor_charges = amount
		
		note_lower = note.text.lower()
		for amount_str in entities.amounts:
			amount_value = extract_amount_value(amount_str)
			# Skip if already categorized or zero
			if amount_value in processed_amounts or amount_value == 0.0:
				continue
			
			# EXCLUDE amounts that are part of total quote or labor charges (identified from projected_earnings)
			if amount_value == pre_identified_total_quote or amount_value == pre_identified_labor_charges:
				# These will be handled in the projected earnings calculation below
				processed_amounts.add(amount_value)
				continue
			
			# Find the context around this amount in the note text
			amount_str_lower = amount_str.lower()
			amount_pos = note_lower.find(amount_str_lower)
			
			# Get context around the amount (100 chars before and after)
			if amount_pos >= 0:
				context_start = max(0, amount_pos - 100)
				context_end = min(len(note_lower), amount_pos + len(amount_str_lower) + 100)
				context = note_lower[context_start:context_end]
			else:
				# Fallback to entire note if amount string not found
				context = note_lower
			
			# EXCLUDE amounts that are clearly part of total quote or labor charges based on context
			if any(phrase in context for phrase in ["total quote", "quote is", "total pot", "total cut", "my total quote", "so my total"]):
				# This is a total quote amount - will be handled in projected earnings calculation
				processed_amounts.add(amount_value)
				continue
			if any(phrase in context for phrase in ["labor charges", "labour charges", "labor fees", "labour fees", "charges will be", "charges are"]):
				# This is a labor charge amount - will be handled in projected earnings calculation
				processed_amounts.add(amount_value)
				continue
			
			# EXCLUDE profit amounts - profit is calculated, not a separate earning/expense
			if any(word in context for word in ["profit", "profit of", "made a profit", "profit after", "profit is"]):
				# This is a profit amount, not an earning or expense - skip it
				processed_amounts.add(amount_value)
				continue
			
			# Check for expense indicators first
			if any(word in context for word in ["will cost", "costs", "cost roughly", "cost about", "adds to", "adds kes"]):
				# Projected expense - add to note_projected_expenses so it's included in earnings calculation
				total_projected_expenses += amount_value
				note_projected_expenses += amount_value
				processed_amounts.add(amount_value)
			elif any(word in context for word in ["spent", "paid for"]):
				# Actual expense
				total_expenses += amount_value
				processed_amounts.add(amount_value)
			elif any(word in context for word in ["paid", "received", "got paid", "they paid", "client paid", "gave me", "deposit"]):
				# Actual earnings - but only if not in a profit context
				# Check if this amount is mentioned in a profit calculation context
				profit_context_words = ["profit", "profit of", "made a profit", "profit after", "profit is"]
				if not any(word in context for word in profit_context_words):
					total_earnings += amount_value
					processed_amounts.add(amount_value)
			# Note: We don't add uncategorized amounts to projected_earnings here
			# because they might be part of a total quote, which we handle below
		
		# NOW calculate projected earnings AFTER fallback has captured all expenses
		# Process PROJECTED earnings (quotes, estimates)
		# If we have total quote, use quote - expenses (profit)
		# If we have labor charges but no total quote, use labor charges
		# Otherwise, use what the LLM extracted
		total_quote_amount = None
		labor_charges_amount = None
		other_projected_earnings = []
		
		# Include labor charges that were incorrectly categorized as expenses
		for amount in labor_charges_from_expenses:
			if labor_charges_amount is None:
				labor_charges_amount = amount
			else:
				# If we already have labor charges, add to other earnings
				other_projected_earnings.append(amount)
		
		for earning_str in entities.projected_earnings:
			earning_lower = earning_str.lower()
			amount = extract_amount_value(earning_str)
			
			# Check if this is a "total quote" (includes everything: materials + labor)
			# Also check for variations like "total pot", "total cut" (transcription errors)
			if any(phrase in earning_lower for phrase in ["total quote", "quote is", "quote to", "total will be", "revised quote", "updated quote", "total pot", "total cut"]):
				total_quote_amount = amount
			# Check if this is labor charges (the actual earnings/profit)
			elif any(phrase in earning_lower for phrase in ["labor charges", "labour charges", "labor fees", "labour fees", "charges will be", "charges are"]):
				labor_charges_amount = amount
			else:
				# Other projected earnings
				other_projected_earnings.append(amount)
		
		# Calculate projected earnings: if we have total quote, use quote - expenses (profit)
		# If we have labor charges but no total quote, use labor charges
		# Otherwise, use other projected earnings
		if total_quote_amount is not None:
			# We have a total quote - earnings = quote - expenses (profit after material costs)
			# note_projected_expenses now includes fallback amounts
			projected_earnings_for_note = total_quote_amount - note_projected_expenses
			if projected_earnings_for_note < 0:
				projected_earnings_for_note = 0.0
			processed_amounts.add(total_quote_amount)
			if labor_charges_amount is not None:
				processed_amounts.add(labor_charges_amount)  # Mark labor charges as processed to avoid double-counting
		elif labor_charges_amount is not None:
			# No total quote, but we have labor charges - use labor charges as earnings
			projected_earnings_for_note = labor_charges_amount
			processed_amounts.add(labor_charges_amount)
		else:
			# No total quote or labor charges, use other projected earnings
			projected_earnings_for_note = sum(other_projected_earnings)
			for amount in other_projected_earnings:
				processed_amounts.add(amount)
		
		# Add calculated earnings to totals
		if projected_earnings_for_note > 0:
			total_projected_earnings += projected_earnings_for_note
	
	# Calculate profits
	net_profit = total_earnings - total_expenses
	projected_profit = total_projected_earnings - total_projected_expenses
	total_combined_earnings = total_earnings + total_projected_earnings
	total_combined_expenses = total_expenses + total_projected_expenses
	combined_profit = total_combined_earnings - total_combined_expenses
	
	return {
		"total_earnings": total_earnings,
		"total_expenses": total_expenses,
		"net_profit": net_profit,
		"total_projected_earnings": total_projected_earnings,
		"total_projected_expenses": total_projected_expenses,
		"projected_profit": projected_profit,
		"total_combined_earnings": total_combined_earnings,
		"total_combined_expenses": total_combined_expenses,
		"combined_profit": combined_profit,
	}
