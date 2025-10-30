from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from backend.app.db import get_db
from backend.app.models import Team, TeamMember, TeamInvite, User
from backend.app.schemas import TeamCreate, TeamOut, TeamMemberOut, TeamInviteCreate, TeamInviteOut
from backend.app.deps import get_current_user

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("", response_model=TeamOut)
def create_team(payload: TeamCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	t = Team(owner_id=current_user.id, name=payload.name)
	db.add(t)
	db.commit()
	db.refresh(t)
	# owner becomes a member with role owner
	m = TeamMember(team_id=t.id, user_id=current_user.id, role="owner")
	db.add(m)
	db.commit()
	return t


@router.get("/{team_id}/members", response_model=list[TeamMemberOut])
def list_members(team_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	t = db.query(Team).filter(Team.id == team_id, Team.owner_id == current_user.id).first()
	if not t:
		raise HTTPException(status_code=404, detail="Team not found")
	members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
	return members


@router.post("/{team_id}/invites", response_model=TeamInviteOut)
def create_invite(team_id: uuid.UUID, payload: TeamInviteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	t = db.query(Team).filter(Team.id == team_id, Team.owner_id == current_user.id).first()
	if not t:
		raise HTTPException(status_code=404, detail="Team not found")
	token = uuid.uuid4().hex
	inv = TeamInvite(team_id=team_id, email=str(payload.email), token=token, accepted=False)
	db.add(inv)
	db.commit()
	db.refresh(inv)
	return inv


@router.post("/invites/{token}", response_model=TeamMemberOut)
def accept_invite(token: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	inv = db.query(TeamInvite).filter(TeamInvite.token == token, TeamInvite.accepted == False).first()  # noqa: E712
	if not inv:
		raise HTTPException(status_code=404, detail="Invite not found or already used")
	# Add member
	m = TeamMember(team_id=inv.team_id, user_id=current_user.id, role="member")
	db.add(m)
	inv.accepted = True
	db.commit()
	db.refresh(m)
	return m
