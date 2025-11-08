from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import logging

from backend.app.db import get_db
from backend.app.models import Client, User
from backend.app.schemas import ClientCreate, ClientOut
from backend.app.deps import get_current_user

router = APIRouter(prefix="/clients", tags=["clients"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ClientOut)
def create_client(payload: ClientCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	c = Client(owner_id=current_user.id, name=payload.name, phone=payload.phone, location=payload.location)
	db.add(c)
	db.commit()
	db.refresh(c)
	return c


@router.get("", response_model=List[ClientOut])
def list_clients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	return db.query(Client).filter(Client.owner_id == current_user.id).order_by(Client.created_at.desc()).all()


# IMPORTANT: /all routes must be defined BEFORE /{id} routes to avoid routing conflicts
@router.delete("/all", status_code=status.HTTP_200_OK)
def delete_all_clients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	"""
	Delete all clients for the current user.
	This will cascade delete associated jobs and notes (via foreign key constraints).
	"""
	clients = db.query(Client).filter(Client.owner_id == current_user.id).all()
	count = len(clients)
	
	for client in clients:
		db.delete(client)
	
	db.commit()
	logger.info(f"Deleted {count} clients for user {current_user.id}")
	
	return {
		"message": f"Deleted {count} clients",
		"count": count
	}


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	c = db.query(Client).filter(Client.id == client_id, Client.owner_id == current_user.id).first()
	if not c:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	return c


@router.put("/{client_id}", response_model=ClientOut)
def update_client(client_id: UUID, payload: ClientCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	c = db.query(Client).filter(Client.id == client_id, Client.owner_id == current_user.id).first()
	if not c:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	c.name = payload.name
	c.phone = payload.phone
	c.location = payload.location
	db.commit()
	db.refresh(c)
	return c


@router.delete("/{client_id}")
def delete_client(client_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	c = db.query(Client).filter(Client.id == client_id, Client.owner_id == current_user.id).first()
	if not c:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
	db.delete(c)
	db.commit()
	return {"ok": True}
