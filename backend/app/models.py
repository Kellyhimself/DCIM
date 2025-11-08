from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db import Base


class TimestampMixin:
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
	updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base, TimestampMixin):
	__tablename__ = "users"

	id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
	full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
	password_hash: Mapped[str] = mapped_column(String(255))

	clients: Mapped[list["Client"]] = relationship(back_populates="owner", cascade="all, delete")
	jobs: Mapped[list["Job"]] = relationship(back_populates="owner", cascade="all, delete")
	notes: Mapped[list["Note"]] = relationship(back_populates="owner", cascade="all, delete", foreign_keys="Note.owner_id")
	assigned_notes: Mapped[list["Note"]] = relationship(back_populates="assignee", cascade="all, delete", foreign_keys="Note.assignee_id")
	owned_teams: Mapped[list["Team"]] = relationship(back_populates="owner", cascade="all, delete")
	team_memberships: Mapped[list["TeamMember"]] = relationship(back_populates="user", cascade="all, delete")
	reminders: Mapped[list["Reminder"]] = relationship(back_populates="owner", cascade="all, delete")


class Team(Base, TimestampMixin):
	__tablename__ = "teams"

	id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
	name: Mapped[str] = mapped_column(String(255))

	owner: Mapped[User] = relationship(back_populates="owned_teams")
	members: Mapped[list["TeamMember"]] = relationship(back_populates="team", cascade="all, delete")
	invites: Mapped[list["TeamInvite"]] = relationship(back_populates="team", cascade="all, delete")


class TeamMember(Base, TimestampMixin):
	__tablename__ = "team_members"

	id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	team_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), index=True)
	user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
	role: Mapped[str] = mapped_column(String(50), default="member")  # owner|member

	team: Mapped[Team] = relationship(back_populates="members")
	user: Mapped[User] = relationship(back_populates="team_memberships")


class TeamInvite(Base, TimestampMixin):
	__tablename__ = "team_invites"

	id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	team_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), index=True)
	email: Mapped[str] = mapped_column(String(255), index=True)
	token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
	accepted: Mapped[bool] = mapped_column(Boolean, default=False)

	team: Mapped[Team] = relationship(back_populates="invites")


class Client(Base, TimestampMixin):
	__tablename__ = "clients"

	id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
	name: Mapped[str] = mapped_column(String(255))
	phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

	owner: Mapped[User] = relationship(back_populates="clients")
	jobs: Mapped[list["Job"]] = relationship(back_populates="client", cascade="all, delete")
	notes: Mapped[list["Note"]] = relationship(back_populates="client", cascade="all, delete")


class Job(Base, TimestampMixin):
	__tablename__ = "jobs"

	id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
	client_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
	site: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
	status: Mapped[str] = mapped_column(String(50), default="open")

	owner: Mapped[User] = relationship(back_populates="jobs")
	client: Mapped[Client] = relationship(back_populates="jobs")
	notes: Mapped[list["Note"]] = relationship(back_populates="job", cascade="all, delete")


class Note(Base, TimestampMixin):
	__tablename__ = "notes"

	id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
	client_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
	job_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
	assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
	text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
	status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, done
	transcription_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, transcribing, completed, failed

	owner: Mapped[User] = relationship(back_populates="notes", foreign_keys=[owner_id])
	assignee: Mapped[Optional[User]] = relationship(back_populates="assigned_notes", foreign_keys=[assignee_id])
	client: Mapped[Optional[Client]] = relationship(back_populates="notes")
	job: Mapped[Optional[Job]] = relationship(back_populates="notes")
	media: Mapped[list["Media"]] = relationship(back_populates="note", cascade="all, delete")


class Media(Base, TimestampMixin):
	__tablename__ = "media"

	id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	note_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), index=True)
	type: Mapped[str] = mapped_column(String(20))  # audio|photo
	key: Mapped[str] = mapped_column(String(512))  # S3 object key
	content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
	uploaded: Mapped[bool] = mapped_column(Boolean, default=False)

	note: Mapped[Note] = relationship(back_populates="media")


class Reminder(Base, TimestampMixin):
	__tablename__ = "reminders"

	id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	owner_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
	note_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("notes.id", ondelete="SET NULL"), nullable=True, index=True)
	job_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
	client_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
	text: Mapped[str] = mapped_column(Text)  # Reminder text (e.g., "return Monday", "call client")
	type: Mapped[str] = mapped_column(String(50), default="follow_up")  # follow_up, call, return, check, meeting, etc.
	due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)  # Parsed due date
	due_date_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Original text (e.g., "Monday", "tomorrow")
	status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, completed, cancelled
	completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

	owner: Mapped[User] = relationship(back_populates="reminders", foreign_keys=[owner_id])
	note: Mapped[Optional[Note]] = relationship(foreign_keys=[note_id])
	job: Mapped[Optional[Job]] = relationship(foreign_keys=[job_id])
	client: Mapped[Optional[Client]] = relationship(foreign_keys=[client_id])
