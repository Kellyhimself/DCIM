from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import User
from backend.app.schemas import UserCreate, UserOut, LoginRequest, Token
from backend.app.security import hash_password, verify_password, create_access_token, create_refresh_token
from backend.app.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
	exists = db.query(User).filter(User.email == payload.email).first()
	if exists:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
	user = User(email=payload.email, full_name=payload.full_name or None, password_hash=hash_password(payload.password))
	db.add(user)
	db.commit()
	db.refresh(user)
	return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
	user = db.query(User).filter(User.email == payload.email).first()
	if not user or not verify_password(payload.password, user.password_hash):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
	access = create_access_token(sub=user.email)
	refresh = create_refresh_token(sub=user.email)
	return Token(access_token=access, refresh_token=refresh)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
	return current_user
