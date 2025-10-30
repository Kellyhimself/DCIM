from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
import base64
import datetime as dt
import httpx

from backend.app.deps import get_current_user
from backend.app.models import User
from backend.app.settings import settings

router = APIRouter(prefix="/billing", tags=["billing"])


def _daraja_base() -> str:
	return "https://sandbox.safaricom.co.ke" if settings.mpesa_env.lower() == "sandbox" else "https://api.safaricom.co.ke"


async def _daraja_token() -> str:
	auth = (settings.mpesa_consumer_key, settings.mpesa_consumer_secret)
	if not all(auth):
		raise HTTPException(status_code=500, detail="M-Pesa credentials not configured")
	async with httpx.AsyncClient(timeout=15) as cx:
		r = await cx.get(f"{_daraja_base()}/oauth/v1/generate?grant_type=client_credentials", auth=auth)
		r.raise_for_status()
		return r.json()["access_token"]


class STKRequest(BaseModel):
	phone: str  # e.g., 2547XXXXXXXX
	amount: int = 10  # KES
	description: str = "Trial payment"


@router.post("/stk")
async def initiate_stk(payload: STKRequest, current_user: User = Depends(get_current_user)):
	now = dt.datetime.now()
	ts = now.strftime("%Y%m%d%H%M%S")
	short_code = settings.mpesa_short_code
	passkey = settings.mpesa_passkey
	callback = settings.mpesa_callback_url or "https://example.com/callback"
	if not (short_code and passkey):
		raise HTTPException(status_code=500, detail="M-Pesa shortcode/passkey not configured")
	password = base64.b64encode(f"{short_code}{passkey}{ts}".encode()).decode()
	access = await _daraja_token()
	headers = {"Authorization": f"Bearer {access}", "Content-Type": "application/json"}
	data = {
		"BusinessShortCode": short_code,
		"Password": password,
		"Timestamp": ts,
		"TransactionType": "CustomerPayBillOnline",
		"Amount": payload.amount,
		"PartyA": payload.phone,
		"PartyB": short_code,
		"PhoneNumber": payload.phone,
		"CallBackURL": callback,
		"AccountReference": str(current_user.id),
		"TransactionDesc": payload.description,
	}
	async with httpx.AsyncClient(timeout=20) as cx:
		r = await cx.post(f"{_daraja_base()}/mpesa/stkpush/v1/processrequest", headers=headers, json=data)
		# don't raise for status; surface response to caller for sandbox debugging
		return {"status_code": r.status_code, "body": r.json() if r.content else {}}


@router.post("/callback")
async def stk_callback(request: Request):
	payload = await request.json()
	# For MVP, just echo back; later persist and verify
	return {"ok": True, "received": payload}
