from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID


class Token(BaseModel):
	access_token: str
	refresh_token: Optional[str] = None
	token_type: str = "bearer"


class UserCreate(BaseModel):
	email: EmailStr
	password: str
	full_name: Optional[str] = None


class UserOut(BaseModel):
	id: UUID
	email: EmailStr
	full_name: Optional[str] = None

	class Config:
		from_attributes = True


class LoginRequest(BaseModel):
	email: EmailStr
	password: str


class ClientCreate(BaseModel):
	name: str
	phone: Optional[str] = None
	location: Optional[str] = None


class ClientOut(BaseModel):
	id: UUID
	name: str
	phone: Optional[str] = None
	location: Optional[str] = None

	class Config:
		from_attributes = True


class JobCreate(BaseModel):
	client_id: str
	site: Optional[str] = None
	status: Optional[str] = "open"


class JobOut(BaseModel):
	id: UUID
	client_id: UUID
	site: Optional[str] = None
	status: str

	class Config:
		from_attributes = True


class MediaOut(BaseModel):
	id: UUID
	type: str
	key: str
	content_type: Optional[str] = None
	uploaded: bool

	class Config:
		from_attributes = True


class NoteCreate(BaseModel):
	client_id: Optional[str] = None
	job_id: Optional[str] = None
	text: Optional[str] = None
	media_type: Optional[str] = None  # audio|photo
	content_type: Optional[str] = None


class NoteUpdate(BaseModel):
	client_id: Optional[str] = None
	job_id: Optional[str] = None
	text: Optional[str] = None


class NoteOut(BaseModel):
	id: UUID
	client_id: Optional[UUID] = None
	job_id: Optional[UUID] = None
	assignee_id: Optional[UUID] = None
	text: Optional[str] = None
	status: str
	transcription_status: str = "pending"
	media: List[MediaOut] = []

	class Config:
		from_attributes = True


class NoteAssignRequest(BaseModel):
	assignee_id: Optional[str] = None  # None to unassign


class NoteStatusRequest(BaseModel):
	status: str  # pending|done


class TranscriptionUpdateRequest(BaseModel):
	status: Optional[str] = None  # pending, transcribing, completed, failed
	text: Optional[str] = None


class PresignResponse(BaseModel):
	upload_url: str
	method: str = "PUT"
	headers: dict
	key: str
	media_id: UUID


class ShareSummaryResponse(BaseModel):
	text: str


class EntityLinkSuggestion(BaseModel):
	type: str  # "client" | "job"
	suggestion: str  # "create" | "link"
	name: str
	phone: Optional[str] = None
	location: Optional[str] = None
	existing_client_id: Optional[str] = None  # If linking to existing client
	existing_job_id: Optional[str] = None  # If linking to existing job
	client_id: Optional[str] = None  # For job creation - the client to link the job to
	job_type: Optional[str] = None  # For job creation - the type of job
	confidence: float = 0.0  # 0.0 to 1.0


class EntityLinkSuggestionsResponse(BaseModel):
	suggestions: List[EntityLinkSuggestion]


class TeamCreate(BaseModel):
	name: str


class TeamOut(BaseModel):
	id: UUID
	name: str
	owner_id: UUID

	class Config:
		from_attributes = True


class TeamMemberOut(BaseModel):
	id: UUID
	team_id: UUID
	user_id: UUID
	role: str

	class Config:
		from_attributes = True


class TeamInviteCreate(BaseModel):
	email: EmailStr


class TeamInviteOut(BaseModel):
	id: UUID
	team_id: UUID
	email: EmailStr
	token: str
	accepted: bool

	class Config:
		from_attributes = True
