from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import User
from backend.app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
	token: HTTPAuthorizationCredentials = Depends(bearer_scheme),
	db: Session = Depends(get_db),
):
	if token is None:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
	payload = decode_token(token.credentials)
	if not payload or payload.get("type") != "access":
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
	user = db.query(User).filter(User.email == payload.get("sub")).first()
	if not user:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
	return user
