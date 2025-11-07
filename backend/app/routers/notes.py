from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import json
import redis
import uuid
import logging
import re
from datetime import datetime

from backend.app.db import get_db
from backend.app.models import Note, Media, User, Client, Job
from backend.app.schemas import NoteCreate, NoteOut, NoteUpdate, PresignResponse, NoteAssignRequest, NoteStatusRequest, ShareSummaryResponse, TranscriptionUpdateRequest, EntityLinkSuggestion, EntityLinkSuggestionsResponse
from backend.app.deps import get_current_user
from backend.app.storage import create_presigned_put, get_s3_client
from backend.app.settings import settings
from backend.app.routers.nlp import extract_entities

router = APIRouter(prefix="/notes", tags=["notes"])

logger = logging.getLogger(__name__)


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
	# Log the URL for debugging
	logger.info(f"Generated presigned URL (first 150 chars): {upload_url[:150]}")
	logger.info(f"S3 endpoint: {settings.s3_endpoint}, Public endpoint: {settings.s3_public_endpoint}")
	return PresignResponse(upload_url=upload_url, headers=headers, key=m.key, media_id=m.id)


@router.post("/{note_id}/upload")
async def upload_media(
	note_id: UUID,
	media_id: UUID,
	file: UploadFile = File(...),
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""Upload media file through backend (alternative to presigned URL upload)."""
	m = db.query(Media).join(Note, Media.note_id == Note.id).filter(
		Media.id == media_id, Note.id == note_id, Note.owner_id == current_user.id
	).first()
	if not m:
		raise HTTPException(status_code=404, detail="Not found")
	
	# Read file content
	contents = await file.read()
	
	# Upload to S3
	s3 = get_s3_client()
	s3.put_object(
		Bucket=settings.s3_bucket,
		Key=m.key,
		Body=contents,
		ContentType=file.content_type or m.content_type,
	)
	
	# Mark as uploaded and finalize
	m.uploaded = True
	if m.type == "audio":
		# Set transcription status to pending
		n = db.query(Note).filter(Note.id == note_id).first()
		if n:
			n.transcription_status = "pending"
		r = get_redis()
		job = {"note_id": str(note_id), "media_id": str(media_id), "key": m.key, "owner_id": str(current_user.id)}
		r.lpush("stt_jobs", json.dumps(job))
	db.commit()
	return {"ok": True, "media_id": str(media_id)}


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


@router.post("/{note_id}/transcription")
def update_transcription(
	note_id: UUID,
	payload: TranscriptionUpdateRequest,
	db: Session = Depends(get_db)
):
	"""Internal endpoint for worker to update transcription. No auth required (internal only)."""
	n = db.query(Note).filter(Note.id == note_id).first()
	if not n:
		raise HTTPException(status_code=404, detail="Not found")
	
	if payload.status is not None:
		n.transcription_status = payload.status
	if payload.text is not None:
		n.text = payload.text
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


@router.put("/{note_id}", response_model=NoteOut)
def update_note(note_id: UUID, payload: NoteUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	"""Update a note's text, client_id, and job_id."""
	n = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
	if not n:
		raise HTTPException(status_code=404, detail="Not found")
	
	if payload.text is not None:
		n.text = payload.text
	
	if payload.client_id is not None:
		if payload.client_id == "":
			n.client_id = None
		else:
			try:
				cid = UUID(payload.client_id)
				# Verify client exists and belongs to user
				client = db.query(Client).filter(Client.id == cid, Client.owner_id == current_user.id).first()
				if not client:
					raise HTTPException(status_code=400, detail="Client not found")
				n.client_id = cid
			except ValueError:
				raise HTTPException(status_code=400, detail="Invalid client_id")
	
	if payload.job_id is not None:
		if payload.job_id == "":
			n.job_id = None
		else:
			try:
				jid = UUID(payload.job_id)
				# Verify job exists and belongs to user
				job = db.query(Job).filter(Job.id == jid, Job.owner_id == current_user.id).first()
				if not job:
					raise HTTPException(status_code=400, detail="Job not found")
				n.job_id = jid
			except ValueError:
				raise HTTPException(status_code=400, detail="Invalid job_id")
	
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
	
	# Extract entities from note text using LLM if available, otherwise regex
	entities = {}
	if n.text:
		extracted = extract_entities(n.text, "KE")
		entities["phones"] = extracted.phones
		entities["amounts"] = extracted.amounts
		entities["dates"] = extracted.dates
		entities["parts"] = extracted.parts
		entities["job_types"] = extracted.job_types
		entities["locations"] = extracted.locations
		entities["client_names"] = extracted.client_names
	
	lines = []
	if client:
		lines.append(f"👤 Client: {client.name}{' (' + client.phone + ')' if client.phone else ''}")
	if job and job.site:
		lines.append(f"📍 Site: {job.site}")
	lines.append(f"📅 Date: {datetime.utcnow().strftime('%Y-%m-%d')}")
	
	# Add key entities if found
	has_entities = False
	if entities.get("phones"):
		lines.append(f"📞 Phone: {', '.join(entities['phones'])}")
		has_entities = True
	if entities.get("amounts"):
		lines.append(f"💰 Amounts: {', '.join(entities['amounts'])}")
		has_entities = True
	if entities.get("dates"):
		lines.append(f"📆 Dates: {', '.join(entities['dates'])}")
		has_entities = True
	if entities.get("parts"):
		lines.append(f"🔧 Parts: {', '.join(entities['parts'])}")
		has_entities = True
	if entities.get("job_types"):
		lines.append(f"🛠️ Job Type: {', '.join(entities['job_types'])}")
		has_entities = True
	if entities.get("locations"):
		lines.append(f"📍 Location: {', '.join(entities['locations'])}")
		has_entities = True
	
	if has_entities:
		lines.append("")  # Empty line before note text
	
	if n.text:
		lines.append(n.text.strip())
	
	if media_count:
		lines.append("")
		lines.append(f"📎 Attachments: {media_count}")
	
	lines.append("")
	lines.append("Thanks,")
	lines.append(current_user.full_name or "Team")
	return ShareSummaryResponse(text="\n".join(lines))


@router.post("/{note_id}/link_suggestions", response_model=EntityLinkSuggestionsResponse)
def get_link_suggestions(note_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	"""Get suggestions for linking extracted entities to clients/jobs."""
	n = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
	if not n:
		raise HTTPException(status_code=404, detail="Not found")
	
	if not n.text:
		return EntityLinkSuggestionsResponse(suggestions=[])
	
	# Extract entities using LLM if available, otherwise regex
	entities = extract_entities(n.text, "KE")
	phones = entities.phones
	client_names = entities.client_names
	locations = entities.locations
	job_types = entities.job_types
	
	logger.info(
		f"[link_suggestions] Note {note_id} - "
		f"Phones: {phones} | "
		f"Client Names: {client_names} | "
		f"Locations: {locations} | "
		f"Job Types: {job_types} | "
		f"Current client_id: {n.client_id} | "
		f"Current job_id: {n.job_id}"
	)
	
	suggestions = []
	
	# Check for client name matches
	for name in client_names:
		# Check if client with this name already exists
		existing_client = db.query(Client).filter(
			Client.owner_id == current_user.id,
			Client.name.ilike(f"%{name}%")
		).first()
		
		if existing_client:
			# Suggest linking to existing client
			suggestions.append(EntityLinkSuggestion(
				type="client",
				suggestion="link",
				name=name,
				phone=existing_client.phone,
				location=existing_client.location,
				existing_client_id=str(existing_client.id),
				confidence=0.8
			))
		else:
			# Suggest creating new client
			# Try to find phone number for this client
			client_phone = None
			if phones:
				client_phone = phones[0]  # Use first phone found
			
			suggestions.append(EntityLinkSuggestion(
				type="client",
				suggestion="create",
				name=name,
				phone=client_phone,
				location=locations[0] if locations else None,
				confidence=0.7
			))
	
	# Check for phone number matches (if no client name but phone exists)
	if phones and not client_names:
		for phone in phones:
			# Check if client with this phone already exists
			existing_client = db.query(Client).filter(
				Client.owner_id == current_user.id,
				Client.phone == phone
			).first()
			
			if existing_client:
				suggestions.append(EntityLinkSuggestion(
					type="client",
					suggestion="link",
					name=existing_client.name,
					phone=phone,
					location=existing_client.location,
					existing_client_id=str(existing_client.id),
					confidence=0.9  # High confidence for phone match
				))
			else:
				# Suggest creating new client with phone
				suggestions.append(EntityLinkSuggestion(
					type="client",
					suggestion="create",
					name="",  # No name found
					phone=phone,
					location=locations[0] if locations else None,
					confidence=0.6
				))
	
	# Suggest creating job if job type and location found, and note not already linked to job
	if job_types and locations and not n.job_id:
		# Match job types to locations based on proximity in text
		# This creates context-aware job suggestions instead of all combinations
		def find_job_location_pairs(text: str, job_types: List[str], locations: List[str]) -> List[tuple]:
			"""Find job type-location pairs based on proximity in text."""
			pairs = []
			text_lower = text.lower()
			
			for job_type in job_types:
				job_type_lower = job_type.lower()
				# Find all occurrences of this job type
				job_matches = list(re.finditer(re.escape(job_type_lower), text_lower))
				
				for job_match in job_matches:
					job_pos = job_match.start()
					# Look for locations within 100 characters before or after the job type
					context_start = max(0, job_pos - 100)
					context_end = min(len(text), job_pos + len(job_type) + 100)
					context = text[context_start:context_end]
					
					# Find the closest location to this job type
					best_location = None
					min_distance = float('inf')
					
					for location in locations:
						location_lower = location.lower()
						# Find location in context
						loc_matches = list(re.finditer(re.escape(location_lower), context.lower()))
						for loc_match in loc_matches:
							# Calculate distance from job type to location
							loc_pos_in_context = loc_match.start()
							loc_pos_in_text = context_start + loc_pos_in_context
							distance = abs(loc_pos_in_text - job_pos)
							
							if distance < min_distance:
								min_distance = distance
								best_location = location
					
					if best_location and min_distance < 150:  # Only if within reasonable distance
						pairs.append((job_type, best_location))
			
			# If no pairs found, fall back to first job type with first location
			if not pairs and job_types and locations:
				pairs.append((job_types[0], locations[0]))
			
			return pairs
		
		# Get context-aware job-location pairs
		job_location_pairs = find_job_location_pairs(n.text, job_types, locations)
		
		# Check if we have a client to link to
		client_id = n.client_id
		if not client_id and client_names:
			# Prioritize the FIRST mentioned client name (primary client)
			# Only use an existing client if it matches the primary client
			primary_client_name = None
			for name in client_names:
				# Skip names that are clearly not real names
				if name.lower() in ['friday', 'friday the', 'monday', 'tuesday', 'wednesday', 'thursday', 'saturday', 'sunday']:
					continue
				primary_client_name = name
				break  # Use the first valid client name
			
			if primary_client_name:
				# Try to find the primary client in database
				client = db.query(Client).filter(
					Client.owner_id == current_user.id,
					Client.name.ilike(f"%{primary_client_name}%")
				).first()
				if client:
					client_id = client.id
					logger.info(f"[link_suggestions] Found primary client '{primary_client_name}' in database: {client_id}")
				else:
					logger.info(f"[link_suggestions] Primary client '{primary_client_name}' not found - job will be created after client creation")
		
		# Suggest one job per unique job_type + location combination
		seen_combinations = set()
		
		# If we have a client_id, suggest creating job
		if client_id:
			for job_type, location in job_location_pairs[:3]:  # Limit to first 3 pairs
				combo = (job_type.lower(), location.lower())
				if combo not in seen_combinations:
					seen_combinations.add(combo)
					suggestions.append(EntityLinkSuggestion(
						type="job",
						suggestion="create",
						name=f"{job_type} - {location}",
						location=location,
						job_type=job_type,
						client_id=str(client_id),
						confidence=0.7
					))
		else:
			# Even without client_id, we can suggest creating a job if we have enough info
			# The user can link the client first, or create the job and link client later
			if client_names or phones:
				# Try to find a potential client_id from names or phones
				# Prioritize the FIRST mentioned client name (primary client)
				potential_client_id = None
				if client_names:
					# Find the primary (first) client name
					primary_client_name = None
					for name in client_names:
						# Skip names that are clearly not real names
						if name.lower() in ['friday', 'friday the', 'monday', 'tuesday', 'wednesday', 'thursday', 'saturday', 'sunday']:
							continue
						primary_client_name = name
						break  # Use the first valid client name
					
					if primary_client_name:
						# Only use this client if it's the primary one
						client = db.query(Client).filter(
							Client.owner_id == current_user.id,
							Client.name.ilike(f"%{primary_client_name}%")
						).first()
						if client:
							potential_client_id = str(client.id)
							logger.info(f"[link_suggestions] Found primary client '{primary_client_name}' for job suggestion: {potential_client_id}")
				
				# Only check phones if primary client not found
				if not potential_client_id and phones:
					# Match phone to primary client if possible
					# For now, use first phone - but ideally match to primary client
					for phone in phones:
						client = db.query(Client).filter(
							Client.owner_id == current_user.id,
							Client.phone == phone
						).first()
						if client:
							# Only use if it matches primary client name
							if client_names:
								primary_name = next((n for n in client_names if n.lower() not in ['friday', 'friday the', 'monday', 'tuesday', 'wednesday', 'thursday', 'saturday', 'sunday']), None)
								if primary_name and primary_name.lower() in client.name.lower():
									potential_client_id = str(client.id)
									logger.info(f"[link_suggestions] Found client by phone matching primary name: {potential_client_id}")
									break
							else:
								# No client names, use phone match
								potential_client_id = str(client.id)
								break
				
				# If we found a client, suggest creating jobs
				if potential_client_id:
					for job_type, location in job_location_pairs[:2]:  # Limit to first 2 pairs
						combo = (job_type.lower(), location.lower())
						if combo not in seen_combinations:
							seen_combinations.add(combo)
							suggestions.append(EntityLinkSuggestion(
								type="job",
								suggestion="create",
								name=f"{job_type} - {location}",
								location=location,
								job_type=job_type,
								client_id=potential_client_id,
								confidence=0.6
							))
				else:
					# No existing client found, but we can still suggest jobs
					# The user will need to create a client first, but we show job suggestions
					# with a note that they need to create the client first
					# Use the PRIMARY (first) client name
					primary_client_name = None
					for name in client_names:
						# Skip names that are clearly not real names
						if name.lower() not in ['friday', 'friday the', 'monday', 'tuesday', 'wednesday', 'thursday', 'saturday', 'sunday']:
							primary_client_name = name
							break  # Use the first valid client name (primary client)
					
					# If we have a primary client name and job types + locations, suggest jobs
					# The job creation will prompt for client creation if needed
					if primary_client_name:
						logger.info(f"[link_suggestions] Suggesting jobs for primary client '{primary_client_name}' (will be created)")
						for job_type, location in job_location_pairs[:2]:  # Limit to first 2 pairs
							combo = (job_type.lower(), location.lower())
							if combo not in seen_combinations:
								seen_combinations.add(combo)
								# Find the phone for this client (match by position in text or use first phone)
								client_phone = phones[0] if phones else None
								# We'll create a temporary client_id hint - but actually, let's require client creation first
								# For now, we'll suggest the job but it will need a client_id
								# The UI should handle this by creating the client first
								suggestions.append(EntityLinkSuggestion(
									type="job",
									suggestion="create",
									name=f"{job_type} - {location}",
									location=location,
									job_type=job_type,
									# No client_id - will need to be set after client creation
									client_id=None,  # Will be set after client is created
									confidence=0.5  # Lower confidence since client doesn't exist
								))
	
	# Also check for existing jobs that might match
	if job_types and locations:
		# Try to find existing jobs with similar site/location
		for location in locations:
			existing_job = db.query(Job).filter(
				Job.owner_id == current_user.id,
				Job.site.ilike(f"%{location}%")
			).first()
			
			if existing_job and existing_job.id != n.job_id:
				suggestions.append(EntityLinkSuggestion(
					type="job",
					suggestion="link",
					name=existing_job.site or f"Job at {location}",
					location=location,
					existing_job_id=str(existing_job.id),
					confidence=0.6
				))
				break  # Only suggest one existing job
	
	logger.info(f"[link_suggestions] Generated {len(suggestions)} suggestions for note {note_id}")
	for i, sug in enumerate(suggestions):
		logger.info(f"[link_suggestions] Suggestion {i+1}: type={sug.type}, suggestion={sug.suggestion}, name={sug.name}, client_id={sug.client_id}, job_id={sug.existing_job_id}")
	
	return EntityLinkSuggestionsResponse(suggestions=suggestions)
