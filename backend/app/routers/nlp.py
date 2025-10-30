#NLP is Natural Language Processing

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
import re
import phonenumbers

from backend.app.deps import get_current_user
from backend.app.models import User

router = APIRouter(prefix="/nlp", tags=["nlp"])


class NLPRequest(BaseModel):
	text: str
	region: Optional[str] = "KE"  # default Kenya


class NLPResponse(BaseModel):
	phones: List[str]
	amounts: List[str]
	dates: List[str]


_amount_patterns = [
	re.compile(r"\b(?:KES|Ksh|KSh|ksh)\s?\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?\b", re.IGNORECASE),
	re.compile(r"\b\d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?\s?(?:KES|Ksh|KSh|ksh)\b", re.IGNORECASE),
]

_date_patterns = [
	re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b", re.IGNORECASE),
	re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
	re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
]


def _extract_phones(text: str, region: str) -> List[str]:
	found = []
	for match in phonenumbers.PhoneNumberMatcher(text, region):
		num = phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)
		found.append(num)
	return list(dict.fromkeys(found))


def _extract_amounts(text: str) -> List[str]:
	vals = []
	for pat in _amount_patterns:
		vals.extend(m.group(0) for m in pat.finditer(text))
	return list(dict.fromkeys(vals))


def _extract_dates(text: str) -> List[str]:
	vals = []
	for pat in _date_patterns:
		vals.extend(m.group(0) for m in pat.finditer(text))
	return list(dict.fromkeys(vals))


@router.post("/tag", response_model=NLPResponse)
async def tag_entities(payload: NLPRequest, current_user: User = Depends(get_current_user)):
	phones = _extract_phones(payload.text, payload.region or "KE")
	amounts = _extract_amounts(payload.text)
	dates = _extract_dates(payload.text)
	return NLPResponse(phones=phones, amounts=amounts, dates=dates)
