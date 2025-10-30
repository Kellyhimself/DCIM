import datetime as dt
from typing import Optional

import jwt
from passlib.context import CryptContext

from backend.app.settings import settings

# Use bcrypt (pinned to a compatible version in requirements.txt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
	return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
	return pwd_context.verify(password, password_hash)


def create_access_token(sub: str, expires_minutes: int = 30) -> str:
	exp = dt.datetime.utcnow() + dt.timedelta(minutes=expires_minutes)
	payload = {"sub": sub, "exp": exp, "type": "access"}
	return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_refresh_token(sub: str, expires_minutes: int = 60 * 24 * 30) -> str:
	exp = dt.datetime.utcnow() + dt.timedelta(minutes=expires_minutes)
	payload = {"sub": sub, "exp": exp, "type": "refresh"}
	return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
	try:
		return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
	except Exception:
		return None
