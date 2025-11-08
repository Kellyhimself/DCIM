#NLP is Natural Language Processing

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import re
import phonenumbers
import logging
import json
import hashlib
import redis

from backend.app.deps import get_current_user
from backend.app.models import User
from backend.app.settings import settings

# Try importing OpenAI, but don't fail if not installed
try:
	from openai import OpenAI
	OPENAI_AVAILABLE = True
except ImportError:
	OPENAI_AVAILABLE = False
	OpenAI = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nlp", tags=["nlp"])

# Redis client for caching LLM responses
_redis_client = None

def get_redis():
	"""Get Redis client singleton."""
	global _redis_client
	if _redis_client is None:
		_redis_client = redis.from_url(settings.redis_url)
	return _redis_client


class NLPRequest(BaseModel):
	text: str
	region: Optional[str] = "KE"  # default Kenya


class NLPResponse(BaseModel):
	phones: List[str]
	amounts: List[str]
	dates: List[str]
	parts: List[str] = []
	client_names: List[str] = []
	job_types: List[str] = []
	locations: List[str] = []
	# Financial tracking - Actual (money already spent/received)
	expenses: List[str] = []  # Money already spent (e.g., "bought materials for 2000", "spent 500 on transport", "paid 1500 for parts")
	earnings: List[str] = []  # Money already received (e.g., "charged 5000", "client paid 8000", "received 3000")
	# Financial tracking - Projected (quotes, estimates, planned costs)
	projected_expenses: List[str] = []  # Planned/future expenses (e.g., "will cost 3000", "adds 2000 to materials", "estimated 1500 for parts")
	projected_earnings: List[str] = []  # Quotes/estimates (e.g., "quote is 43000", "estimated 5000", "will charge 8000")
	# Reminders and actions
	reminders: List[dict] = []  # [{text: "return Monday", due_date: "Monday", type: "follow_up"}]
	shopping_items: List[str] = []  # Items to buy (e.g., "need to buy 3 elbows", "bring plunger")


_amount_patterns = [
	re.compile(r"\b(?:KES|Ksh|KSh|ksh)\s?\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?\b", re.IGNORECASE),
	re.compile(r"\b\d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?\s?(?:KES|Ksh|KSh|ksh)\b", re.IGNORECASE),
	re.compile(r"\b(?:Kenyan\s+)?shillings?\s+\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?\b", re.IGNORECASE),
	re.compile(r"\b\d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?\s+shillings?\b", re.IGNORECASE),
	# Match "8000 Kenyan shillings" or "2000 Kenyan shillings" - amount followed by "Kenyan shillings"
	# Match amounts with 3+ digits (like "8000", "2000", "12000")
	re.compile(r"\b(\d{3,}(?:\.\d+)?)\s+Kenyan\s+shillings?\b", re.IGNORECASE),
	# Also match amounts with commas (like "8,000" or "2,000")
	re.compile(r"\b(\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?)\s+Kenyan\s+shillings?\b", re.IGNORECASE),
	re.compile(r"\b\d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?\s*(?:shillings?|KES|Ksh)\b", re.IGNORECASE),
	# Standalone amounts with commas (like "3,500", "2,500", "1,500") - be careful not to match phone numbers or years
	# Match amounts that have at least 4 digits total (to avoid matching short numbers)
	re.compile(r"\b(?<![\d+])\d{1,3}[,\s]\d{3,}\b(?!\s*(?:shillings?|KES|Ksh|phone|call|contact|\d{4}))", re.IGNORECASE),
	# Amounts followed by "labour" or "labor" (like "1,500" in "labour is 1,500")
	re.compile(r"\b\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?\s+(?:labour|labor)\b", re.IGNORECASE),
	# Amounts after "labour is" or "labor is" (like "labour is 1,500")
	re.compile(r"\b(?:labour|labor)\s+is\s+(\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?)\b", re.IGNORECASE),
]

_date_patterns = [
	# Patterns like "Friday 17th" or "Friday the 17th" - day name followed by date
	re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(?:the\s+)?\d{1,2}(?:st|nd|rd|th)?\b", re.IGNORECASE),
	re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b", re.IGNORECASE),
	re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b", re.IGNORECASE),
	re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
	re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
	# Patterns like "15th of January 2025", "15th January", "January 15th", etc.
	re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b", re.IGNORECASE),
	re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*\d{4}\b", re.IGNORECASE),
	re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\b", re.IGNORECASE),
	re.compile(r"\b(?:next|this|last)\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b", re.IGNORECASE),
]

# Trade dictionaries for blue-collar work in Kenya
_PLUMBING_PARTS = [
	"p-trap", "ptrap", "p trap", "pit trap", "pit-trap", "u-bend", "ubend", "u bend", "pipe", "pipes", "fitting", "fittings",
	"faucet", "tap", "taps", "valve", "valves", "sink", "sinks", "toilet", "toilets", "cistern",
	"shower", "showers", "bathtub", "bath tub", "water heater", "geyser", "geysers", "pump", "pumps",
	"drain", "drains", "sewer", "sewers", "gutter", "gutters", "water meter", "water meters",
	"elbow", "elbows", "tee", "tees", "coupling", "couplings", "nipple", "nipples", "reducer", "reducers",
	"ball valve", "gate valve", "check valve", "pressure valve", "stopcock", "stopcocks",
	"washer", "washers", "gasket", "gaskets", "o-ring", "o ring", "seal", "seals",
	"pipe wrench", "pipe wrenches", "plunger", "plungers", "auger", "augers",
]

_ELECTRICAL_PARTS = [
	"wire", "wires", "cable", "cables", "switch", "switches", "socket", "sockets", "outlet", "outlets",
	"bulb", "bulbs", "light", "lights", "lamp", "lamps", "fixture", "fixtures", "circuit breaker",
	"fuse", "fuses", "fuse box", "fuse boxes", "panel", "panels", "meter", "meters", "transformer",
	"conduit", "conduits", "junction box", "junction boxes", "terminal", "terminals", "connector", "connectors",
	"plug", "plugs", "adapter", "adapters", "extension cord", "extension cords", "multimeter", "multimeters",
	"wire stripper", "wire strippers", "crimper", "crimpers", "soldering iron", "soldering irons",
	"led", "leds", "fluorescent", "halogen", "incandescent", "cfl",
]

_CARPENTRY_PARTS = [
	"board", "boards", "plank", "planks", "beam", "beams", "joist", "joists", "stud", "studs",
	"nail", "nails", "screw", "screws", "bolt", "bolts", "nut", "nuts", "washer", "washers",
	"hinge", "hinges", "handle", "handles", "lock", "locks", "door", "doors", "window", "windows",
	"frame", "frames", "trim", "trims", "molding", "moldings", "shelf", "shelves", "cabinet", "cabinets",
	"saw", "saws", "drill", "drills", "hammer", "hammers", "chisel", "chisels", "plane", "planes",
	"plywood", "hardwood", "softwood", "mdf", "particle board", "particle boards",
]

_GENERAL_PARTS = [
	"tool", "tools", "material", "materials", "supply", "supplies", "part", "parts", "component", "components",
	"equipment", "machinery", "machine", "machines", "motor", "motors", "engine", "engines",
	"battery", "batteries", "filter", "filters", "belt", "belts", "chain", "chains",
]

_ALL_PARTS = _PLUMBING_PARTS + _ELECTRICAL_PARTS + _CARPENTRY_PARTS + _GENERAL_PARTS

_JOB_TYPES = [
	"plumbing", "plumber", "plumbers", "plumb", "plumbed",
	"electrical", "electrician", "electricians", "electric", "electrics",
	"carpentry", "carpenter", "carpenters", "carpentry work",
	"repair", "repairs", "repairing", "fixed", "fix", "fixing",
	"installation", "install", "installing", "installed", "installs",
	"maintenance", "maintain", "maintaining", "maintained",
	"renovation", "renovate", "renovating", "renovated",
	"construction", "construct", "constructing", "constructed",
	"painting", "paint", "painted", "paints",
	"welding", "weld", "welded", "welds",
	"masonry", "mason", "masons", "bricklaying", "bricklayer",
	"roofing", "roof", "roofs", "roofer", "roofers",
	"tiling", "tile", "tiles", "tiler", "tilers",
	"plastering", "plaster", "plasters", "plasterer", "plasterers",
]

# Common Kenyan locations (neighborhoods, areas, estates)
_KENYAN_LOCATIONS = [
	"westlands", "kilimani", "lavington", "karen", "rongai", "kasarani", "runda", "muthaiga",
	"parklands", "westlands", "hurlingham", "kilimani", "loresho", "spring valley",
	"kileleshwa", "nyali", "bamburi", "shanzu", "mombasa", "nairobi", "kisumu", "nakuru",
	"eldoret", "thika", "naivasha", "machakos", "kajiado", "kiambu", "ruiru", "juja",
	"embakasi", "kawangware", "kibera", "mathare", "dandora", "kayole", "buruburu", "donholm",
	"eastleigh", "pangani", "parklands", "westlands", "kilimani", "lavington",
	"ngong", "langata", "karen", "rongai", "kiserian", "ongata rongai",
	"ruai", "kasarani", "roysambu", "githurai", "kahawa", "west", "east", "south", "north",
	"cbd", "city center", "town", "downtown", "uptown",
]

# Common Kenyan names (first names and surnames)
_KENYAN_NAMES = [
	"wanjiru", "wambui", "njeri", "nyambura", "wairimu", "wangui", "wacera", "wanja",
	"kamau", "kariuki", "njoroge", "mwangi", "kinyua", "kibet", "kipchoge", "kiprotich",
	"otieno", "odhiambo", "okoth", "okello", "omondi", "onyango", "okumu",
	"muthoni", "mumbi", "makena", "makena", "makena", "makena",
	"james", "john", "peter", "paul", "joseph", "josephine", "mary", "ann", "anne",
	"david", "daniel", "samuel", "samuel", "stephen", "steven", "thomas", "william",
	"grace", "faith", "hope", "joy", "peace", "mercy", "prudence",
	"mutua", "musyoka", "kilonzo", "kivindu", "mutinda", "mutiso",
	"chebet", "chepkoech", "chepngetich", "cherotich", "cherono",
	"akinyi", "adhiambo", "aoko", "anyango", "atieno",
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
		matches = list(pat.finditer(text))
		for m in matches:
			# Handle patterns with capture groups (like "labour is 1,500")
			if m.groups():
				amount = m.group(1)  # Get the captured amount
			else:
				amount = m.group(0)  # Get the full match
			
			# Filter out phone numbers (10+ digits) and standalone 4-digit years
			digits_only = re.sub(r'[^\d]', '', amount)
			if len(digits_only) < 10:  # Phone numbers are usually 10+ digits
				# Check if it's a year (4 digits, possibly with commas)
				if len(digits_only) == 4 and (1900 <= int(digits_only) <= 2100):
					# Likely a year, skip it
					continue
				# Only add if it has at least 3 digits (to avoid matching single/double digits)
				if len(digits_only) >= 3:
					vals.append(amount)
	return list(dict.fromkeys(vals))


def _extract_dates(text: str) -> List[str]:
	vals = []
	for pat in _date_patterns:
		vals.extend(m.group(0) for m in pat.finditer(text))
	return list(dict.fromkeys(vals))


def _extract_parts(text: str) -> List[str]:
	"""Extract trade parts (plumbing, electrical, carpentry, etc.) from text."""
	found = []
	text_lower = text.lower()
	
	# Check for each part in the dictionary
	for part in _ALL_PARTS:
		# Use word boundaries to avoid partial matches
		pattern = r'\b' + re.escape(part.lower()) + r'\b'
		if re.search(pattern, text_lower, re.IGNORECASE):
			# Find the actual occurrence in the original text (preserve case)
			matches = re.finditer(re.escape(part), text, re.IGNORECASE)
			for match in matches:
				found.append(match.group(0))
	
	return list(dict.fromkeys(found))


def _extract_job_types(text: str) -> List[str]:
	"""Extract job types from text."""
	found = []
	text_lower = text.lower()
	
	for job_type in _JOB_TYPES:
		pattern = r'\b' + re.escape(job_type.lower()) + r'\b'
		if re.search(pattern, text_lower, re.IGNORECASE):
			matches = re.finditer(re.escape(job_type), text, re.IGNORECASE)
			for match in matches:
				found.append(match.group(0))
	
	return list(dict.fromkeys(found))


def _extract_locations(text: str) -> List[str]:
	"""Extract locations (Kenyan neighborhoods, areas, cities) from text."""
	found = []
	text_lower = text.lower()
	
	for location in _KENYAN_LOCATIONS:
		pattern = r'\b' + re.escape(location.lower()) + r'\b'
		if re.search(pattern, text_lower, re.IGNORECASE):
			matches = re.finditer(re.escape(location), text, re.IGNORECASE)
			for match in matches:
				found.append(match.group(0))
	
	# Also look for common location patterns - be more careful to avoid extracting too much
	location_patterns = [
		# Match "from [Location]" or "in [Location]" but not "from [Name] called from [Location]"
		re.compile(r'\b(?:in|at|near|around|from)\s+([A-Z][a-z]+)\s+(?:area|estate|road|street|avenue|drive|lane|place|office|house|home)\b', re.IGNORECASE),
		re.compile(r'\b([A-Z][a-z]+)\s+(?:area|estate|road|street|avenue|drive|lane)\b', re.IGNORECASE),
		# Match standalone location names after prepositions, but be careful
		# Only match if it's a single capitalized word (not a phrase)
		re.compile(r'\b(?:in|at|near|around|from)\s+([A-Z][a-z]+)\b(?!\s+(?:called|phone|number|contact|client|customer|\w+\s+\w+))', re.IGNORECASE),
	]
	
	for pattern in location_patterns:
		for match in pattern.finditer(text):
			potential_location = match.group(1)
			# Filter out common false positives, names, and words that are clearly not locations
			exclude_words = ['the', 'this', 'that', 'here', 'there', 'where', 'wanjiru', 'client', 'customer', 'owner', 
			                 'sarah', 'david', 'john', 'james', 'peter', 'paul', 'mary', 'ann', 'friday', 'monday', 
			                 'tuesday', 'wednesday', 'thursday', 'saturday', 'sunday', 'called', 'phone', 'number',
			                 'mdoni', 'ochieng', 'kamau', 'muthoni', 'update', 'quick']
			if potential_location.lower() not in exclude_words:
				# Check if it's followed by possessive ('s) - if so, it's likely a name, not a location
				match_end = match.end()
				if match_end < len(text) and text[match_end:match_end+2].lower() not in ["'s", "'"]:
					# Only add if it's a known location or matches our location dictionary
					if potential_location.lower() in [loc.lower() for loc in _KENYAN_LOCATIONS]:
						if len(potential_location) > 2:  # Avoid very short matches
							found.append(potential_location)
					else:
						# For unknown locations, be more conservative - only if it's clearly a location context
						match_start = match.start()
						if match_start > 0:
							before_text = text[max(0, match_start-30):match_start].lower()
							# Only if we see location-indicating words before it
							if any(word in before_text for word in ['in ', 'at ', 'from ', 'near ', 'around ', 'area', 'estate']):
								# And make sure it's not part of a name phrase
								if 'called' not in before_text[-15:] or 'from' in before_text[-10:]:
									if len(potential_location) > 2:
										found.append(potential_location)
	
	return list(dict.fromkeys(found))


def _extract_client_names(text: str) -> List[str]:
	"""Extract potential client names from text."""
	found = []
	text_lower = text.lower()
	
	# Check for known Kenyan names
	for name in _KENYAN_NAMES:
		pattern = r'\b' + re.escape(name.lower()) + r'\b'
		if re.search(pattern, text_lower, re.IGNORECASE):
			matches = re.finditer(re.escape(name), text, re.IGNORECASE)
			for match in matches:
				found.append(match.group(0))
	
	# Look for patterns like "client's name", "for [Name]", "call [Name]", etc.
	name_patterns = [
		re.compile(r'\b(?:for|call|contact|client|customer|owner)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', re.IGNORECASE),
		# Pattern for possessive - capture full name (one or two words) before apostrophe
		# "David Ochieng's place" should capture "David Ochieng", not just "Ochieng"
		re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'s\s+(?:house|home|place|office|shop|business)\b", re.IGNORECASE),
		re.compile(r'\b(?:mr|mrs|miss|ms|dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', re.IGNORECASE),
		# Pattern for "Sarah called" or "Name called" - capture the name before "called"
		# Also capture full names like "Sarah Mbdoni called"
		re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+called\s+(?:from|at|in)\b', re.IGNORECASE),
		# Pattern for "Sarah Mbdoni" or "David Ochieng" - two capitalized words together
		# But exclude common phrases like "Quick update", "Also remember", etc.
		re.compile(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b(?!\s+(?:called|phone|number|contact|client|customer|update|remember|also|scheduled|\w+\s+\w+))', re.IGNORECASE),
	]
	
	# Exclude common false positives (days of week, common words, phrases, etc.)
	exclude_names = ['the', 'this', 'that', 'here', 'there', 'where', 'job', 'work', 'friday', 'monday', 
	                 'tuesday', 'wednesday', 'thursday', 'saturday', 'sunday', 'january', 'february', 
	                 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 
	                 'december', 'next', 'this', 'last', 'total', 'both', 'around', 'about', 'still', 'need',
	                 'quick', 'update', 'okay', 'remember', 'also', 'scheduled', 'but', 'reminder']
	
	# Exclude common phrases that might be matched as names
	exclude_phrases = ['quick update', 'quick reminder', 'also remember', 'but remember', 'also need', 
	                   'still need', 'also check', 'also want', 'also have', 'also see', 'also do', 
	                   'also get', 'also make', 'also call', 'also contact', 'also find', 'also add', 
	                   'also remove', 'also replace', 'also install', 'also fix', 'also repair', 
	                   'also check', 'kenyan shillings', 'kenyan shilling', 'shillings', 'shilling']  # Currency phrases
	
	# Days of week and date-related phrases to exclude
	date_phrases = ['friday', 'monday', 'tuesday', 'wednesday', 'thursday', 'saturday', 'sunday',
	                'friday the', 'monday the', 'tuesday the', 'wednesday the', 'thursday the', 
	                'saturday the', 'sunday the']
	
	for pattern in name_patterns:
		for match in pattern.finditer(text):
			potential_name = match.group(1)
			# Filter out common false positives
			if potential_name.lower() not in exclude_names:
				# Check if it's an excluded phrase
				if potential_name.lower() in exclude_phrases:
					continue
				# Check if it contains a day of week (like "Friday the")
				if any(phrase in potential_name.lower() for phrase in date_phrases):
					continue
				# Check if it starts with a day of week
				words = potential_name.split()
				if words and words[0].lower() in ['friday', 'monday', 'tuesday', 'wednesday', 'thursday', 'saturday', 'sunday']:
					continue
				# Check if it starts with common non-name words
				if words and words[0].lower() in ['quick', 'also', 'still', 'then', 'now', 'here', 'there', 'where', 'kenyan', 'but', 'remember', 'reminder']:
					continue
				# Check if it contains currency-related words
				if any(word in potential_name.lower() for word in ['shilling', 'shillings', 'kes', 'ksh']):
					continue
				if len(potential_name) > 2 and potential_name[0].isupper():  # Must start with capital
					# Additional check: if it's a single word that's a day of week, skip it
					if potential_name.lower() not in ['friday', 'monday', 'tuesday', 'wednesday', 'thursday', 'saturday', 'sunday']:
						found.append(potential_name)
	
	# Remove duplicates and substrings
	# If we have "David Ochieng", remove "David" as a separate entry
	unique_names = []
	for name in found:
		# Check if this name is a substring of another name
		is_substring = False
		for other_name in found:
			if name != other_name and name.lower() in other_name.lower():
				# If name is a single word and appears in a multi-word name, skip it
				if len(name.split()) == 1 and len(other_name.split()) > 1:
					is_substring = True
					break
		if not is_substring:
			unique_names.append(name)
	
	return list(dict.fromkeys(unique_names))


def _extract_entities_with_llm(text: str, region: str = "KE") -> Optional[NLPResponse]:
	"""Extract entities using OpenAI GPT. Returns None if API key not configured or on error."""
	# Get API key from settings (matches OPENAI_API_KEY env var due to case_sensitive=False)
	api_key = settings.openai_api_key
	if not OPENAI_AVAILABLE:
		logger.info("[NLP-LLM] OpenAI library not available, skipping LLM extraction")
		return None
	if not api_key:
		logger.info("[NLP-LLM] OPENAI_API_KEY not set, skipping LLM extraction")
		return None
	
	logger.info(f"[NLP-LLM] Attempting LLM extraction for text (length: {len(text)})")
	
	try:
		client = OpenAI(api_key=api_key)
		
		prompt = f"""Extract structured job data from this voice note transcription. The context is blue-collar work in Kenya (plumbing, electrical, carpentry, construction, masonry, welding, tailoring, painting, roofing, tiling, landscaping, etc.).

Text: "{text}"

Extract the following entities and return ONLY valid JSON (no markdown, no explanation):

ENTITY CATEGORIES:

1. phones: List of phone numbers (format: +254XXXXXXXXX or 07XXXXXXXX or 07XX-XXX-XXX)
   Examples: ["0798123456", "0789234567", "+254712345678"]

2. amounts: List of ALL monetary amounts mentioned (in Kenyan shillings, KES, Ksh, etc.)
   Examples: ["1800", "300", "5000", "45000", "20000", "65000"]

3. dates: List of dates mentioned (e.g., "Monday", "Friday 17th", "15th of February", "next Friday", "tomorrow", "next week")
   Examples: ["Tuesday", "Sunday", "15th of February", "20th of February", "next week", "two weeks", "6 months"]

4. parts: List of parts/tools/materials mentioned
   Examples: ["premium thread", "zippers", "bricks", "cement", "iron sheets", "gutters", "ceramic tiles", "grout", "tile adhesive"]

5. client_names: List of client/customer names mentioned
   IMPORTANT: Extract names accurately - preserve exact spelling. If you see "Collins Otieno" extract it as "Collins Otieno" not "Colin Sotieno". 
   If you see "Call Collins" or "follow up with Collins", extract "Collins" as a client name.
   Examples: ["Beatrice Nyambura", "Collins Otieno", "Grace Wambui", "Francis Kariuki", "Lucy", "Joseph Mutua", "Agnes Njeri"]

6. job_types: List of job types mentioned
   Examples: ["tailoring", "masonry", "welding", "tiling", "painting", "roofing", "landscaping", "plumbing", "electrical", "carpentry"]

7. locations: List of locations/areas mentioned
   Examples: ["Runda", "Ngong", "Thika", "Ruaka", "Kasarani", "Kiambu", "Limuru"]

8. expenses: List of ACTUAL expenses (money already spent - past tense)
   Key indicators: "spent", "paid", "bought", "purchased", "I paid", "I spent", "I bought"
   Examples: 
   - "spent 1,800 shillings on premium thread and zippers"
   - "paid 300 shillings for a matatu ride"
   - "bought iron sheets for 22,000 shillings"
   - "purchased some foundation materials for 12,000 shillings last week"
   - "spent 2,000 shillings on transport today"
   - "paid 800 shillings for parking today"
   - "Spent 35,000 shillings on plants and soil"
   - "Paid 4,500 shillings for delivery"
   - "spent 8,000 shillings on some initial metal sheets"
   Do NOT include: future costs, estimates, profit amounts, labor charges

9. earnings: List of ACTUAL earnings (money already received - past tense)
   Key indicators: "paid me", "received", "got paid", "gave me", "sent me", "client paid", "they paid"
   Examples:
   - "client gave me 5,000 shillings as deposit"
   - "client paid me 35,000 shillings for the completed work"
   - "received 15,000 shillings from the client today as advance payment"
   - "client paid me 40,000 shillings for the roofing service"
   - "received 80,000 shillings as the first payment"
   - "client has sent me 20,000 shillings"
   Do NOT include: quotes, estimates, profit amounts

10. projected_expenses: List of PROJECTED/PLANNED expenses (future costs, estimates)
    Key indicators: "will cost", "will cost roughly", "costs roughly", "cost roughly", "adds to", "estimated", "worth about", "approximately"
    Examples:
    - "total alteration cost will be around 4,500 shillings including materials"
    - "bricks and cement will cost roughly 45,000 Kenyan shillings"
    - "increases the material cost by KES 8,000"
    - "materials will cost approximately 18,000 shillings"
    - "additional paint and brushes will cost about 7,500 shillings"
    - "additional plants and irrigation pipes worth about 45,000 shillings"
    CRITICAL: Do NOT extract "labor charges", "labour charges", "labor fees", or "labour fees" as projected_expenses - these are ALWAYS projected_earnings.

11. projected_earnings: List of PROJECTED earnings (quotes, estimates, planned charges, labor charges/fees)
    Key indicators: "quote is", "quoted at", "total quote", "total pot", "total cut", "total will be", "revised quote", "updated quote", "will pay", "will charge", "labor charges", "labour charges"
    Examples:
    - "total quote is 65,000 Kenyan shillings"
    - "Labour charges will be 20,000 shillings"
    - "revised the quote to KES 73,000 total"
    - "they'll pay 45,000 shillings once the tiling is complete"
    - "Total project value is 55,000 shillings"
    - "total project quote is 280,000 shillings"
    - "total job is quoted at 50,000 shillings"
    IMPORTANT: If both "total quote" (or variations like "total pot", "total cut") and "labor charges" are mentioned, extract BOTH separately.
    CRITICAL: "labor charges", "labour charges", "labor fees", "labour fees" are NEVER expenses - they are ALWAYS projected_earnings.

12. reminders: List of reminder objects with text, due_date, and type
    Extract ALL action items with due dates or timeframes. Types: "call", "return", "follow_up", "check", "meeting", "remind"
    Examples:
    - {{"text": "return on Tuesday for the final fitting", "due_date": "Tuesday", "type": "return"}}
    - {{"text": "call her on Sunday to confirm the appointment time", "due_date": "Sunday", "type": "call"}}
    - {{"text": "Follow up with Collins on Thursday to finalize the contract", "due_date": "Thursday", "type": "follow_up"}}
    - {{"text": "Call Collins at 0789234567 to confirm", "due_date": "soon", "type": "call"}}
    - {{"text": "Check back next week to see if they've signed the contract", "due_date": "next week", "type": "check"}}
    - {{"text": "return in two weeks to check on the gate hinges and apply rust protection", "due_date": "two weeks", "type": "return"}}
    - {{"text": "call them tomorrow to schedule when to start", "due_date": "tomorrow", "type": "call"}}
    - {{"text": "return on Wednesday to continue painting", "due_date": "Wednesday", "type": "return"}}
    - {{"text": "follow up with the client on Monday to confirm the color choices", "due_date": "Monday", "type": "follow_up"}}
    - {{"text": "Check the first coat on Friday to see if it needs a second layer", "due_date": "Friday", "type": "check"}}
    - {{"text": "call them next week to check if there are any leaks", "due_date": "next week", "type": "call"}}
    - {{"text": "remind them to come back in 6 months for roof maintenance inspection", "due_date": "6 months", "type": "follow_up"}}
    - {{"text": "meet with the client on Thursday to discuss the garden design", "due_date": "Thursday", "type": "meeting"}}
    - {{"text": "call the nursery tomorrow to order the next batch of plants", "due_date": "tomorrow", "type": "call"}}
    - {{"text": "Check the site on Monday to ensure the soil preparation is complete", "due_date": "Monday", "type": "check"}}
    - {{"text": "return to the Ruaka job site on Friday to check the tile alignment", "due_date": "Friday", "type": "return"}}
    - {{"text": "call them before I go to confirm they'll be home", "due_date": "before Friday", "type": "call"}}
    IMPORTANT: Extract every reminder mentioned, even if multiple reminders are in one note. Include the full reminder text.

13. shopping_items: List of items to buy/bring/get
    Key indicators: "need to buy", "bring", "get", "buy", "need", "bring when I go back"
    Examples:
    - ["ceramic tiles", "grout", "tile adhesive", "tile cutter", "leveling tools"]
    - ["rust protection"]
    - ["quality sand", "ballast"]
    - ["3 elbows", "plunger", "new tap washers", "drain snake"]

EXTRACTION RULES:
- Only extract entities that are clearly mentioned in the text
- For client names: Extract full names when possible. Preserve exact spelling and spacing.
- For amounts: Include currency context if mentioned, otherwise just the number
- For dates: Preserve the format as mentioned (e.g., "15th of February", "next week", "two weeks")
- For locations: Use proper capitalization
- For job_types: Extract explicit job types mentioned
- For expenses: ONLY past tense actual expenses. Do NOT include profit amounts.
- For earnings: ONLY past tense actual earnings. Do NOT include profit amounts.
- For projected_expenses: ONLY future costs/estimates. NEVER include labor charges.
- For projected_earnings: Quotes, estimates, labor charges. Include phrases like "total project value", "total job is quoted at".
- For reminders: Extract ALL action items with due dates. Include full reminder text.
- For shopping_items: Extract items mentioned with buying/bringing indicators.
- Return empty arrays [] if no entities found for a category
- Do NOT extract false positives like "Friday the" as a client name, or "Quick update" as a name

Return JSON in this exact format:
{{
  "phones": ["0798123456", "0789234567"],
  "amounts": ["1800", "300", "5000", "45000", "20000", "65000"],
  "dates": ["Tuesday", "Sunday", "15th of February", "next week"],
  "parts": ["premium thread", "zippers", "bricks", "cement"],
  "client_names": ["Beatrice Nyambura", "Collins Otieno", "Grace Wambui"],
  "job_types": ["tailoring", "masonry", "welding"],
  "locations": ["Runda", "Ngong", "Thika"],
  "expenses": ["spent 1,800 shillings on premium thread and zippers", "paid 300 shillings for a matatu ride"],
  "earnings": ["client gave me 5,000 shillings as deposit"],
  "projected_expenses": ["total alteration cost will be around 4,500 shillings including materials", "bricks and cement will cost roughly 45,000 Kenyan shillings"],
  "projected_earnings": ["total quote is 65,000 Kenyan shillings", "Labour charges will be 20,000 shillings"],
  "reminders": [
    {{"text": "return on Tuesday for the final fitting", "due_date": "Tuesday", "type": "return"}},
    {{"text": "call her on Sunday to confirm the appointment time", "due_date": "Sunday", "type": "call"}},
    {{"text": "Follow up with Collins on Thursday to finalize the contract", "due_date": "Thursday", "type": "follow_up"}}
  ],
  "shopping_items": ["ceramic tiles", "grout", "tile adhesive", "tile cutter", "leveling tools"]
}}"""

		logger.info(f"[NLP-LLM] Sending request to OpenAI GPT-4o-mini...")
		response = client.chat.completions.create(
			model="gpt-4o-mini",
			messages=[
				{"role": "system", "content": "You are a helpful assistant that extracts structured data from voice notes. Always return valid JSON only."},
				{"role": "user", "content": prompt}
			],
			response_format={"type": "json_object"},
			temperature=0.1,  # Low temperature for consistent extraction
		)
		
		result_text = response.choices[0].message.content
		logger.info(f"[NLP-LLM] Raw JSON response from OpenAI: {result_text}")
		
		result_json = json.loads(result_text)
		logger.info(f"[NLP-LLM] Parsed JSON: {json.dumps(result_json, indent=2)}")
		
		# Validate and convert to NLPResponse
		nlp_response = NLPResponse(
			phones=result_json.get("phones", []),
			amounts=result_json.get("amounts", []),
			dates=result_json.get("dates", []),
			parts=result_json.get("parts", []),
			client_names=result_json.get("client_names", []),
			job_types=result_json.get("job_types", []),
			locations=result_json.get("locations", []),
			expenses=result_json.get("expenses", []),
			earnings=result_json.get("earnings", []),
			projected_expenses=result_json.get("projected_expenses", []),
			projected_earnings=result_json.get("projected_earnings", []),
			reminders=result_json.get("reminders", []),
			shopping_items=result_json.get("shopping_items", []),
		)
		
		logger.info(f"[NLP-LLM] Successfully extracted entities - "
		           f"Phones: {nlp_response.phones} | "
		           f"Amounts: {nlp_response.amounts} | "
		           f"Dates: {nlp_response.dates} | "
		           f"Parts: {nlp_response.parts} | "
		           f"Job Types: {nlp_response.job_types} | "
		           f"Locations: {nlp_response.locations} | "
		           f"Client Names: {nlp_response.client_names} | "
		           f"Expenses: {nlp_response.expenses} | "
		           f"Earnings: {nlp_response.earnings} | "
		           f"Projected Expenses: {nlp_response.projected_expenses} | "
		           f"Projected Earnings: {nlp_response.projected_earnings} | "
		           f"Reminders: {len(nlp_response.reminders)} | "
		           f"Shopping Items: {nlp_response.shopping_items}")
		
		return nlp_response
	except json.JSONDecodeError as e:
		logger.error(f"[NLP-LLM] JSON decode error: {e}. Raw response: {result_text if 'result_text' in locals() else 'N/A'}")
		return None
	except Exception as e:
		logger.error(f"[NLP-LLM] Error extracting entities with LLM: {e}", exc_info=True)
		return None


def extract_entities(text: str, region: str = "KE", force_refresh: bool = False) -> NLPResponse:
	"""
	Extract entities from text using LLM if available, otherwise regex.
	This is a shared function that can be used by both /nlp/tag and link_suggestions.
	Uses Redis caching to avoid duplicate LLM calls for the same text.
	Different voice notes (different text) will have different hashes and will fetch fresh data.
	
	Args:
		text: The text to extract entities from
		region: The region code (default: "KE")
		force_refresh: If True, bypass cache and force fresh extraction
	"""
	# Create cache key from text hash (different text = different hash = new fetch)
	text_hash = hashlib.sha256(f"{text}:{region}".encode()).hexdigest()
	cache_key = f"nlp:extract:{text_hash}"
	text_preview = text[:100].replace('\n', ' ') if len(text) > 100 else text.replace('\n', ' ')
	
	if force_refresh:
		logger.info(f"[NLP-Cache] 🔄 FORCE REFRESH requested - bypassing cache (hash: {text_hash[:16]}... | preview: \"{text_preview}...\")")
		# Delete cache if it exists
		try:
			redis_client = get_redis()
			redis_client.delete(cache_key)
			logger.info(f"[NLP-Cache] 🗑️  Cleared cache for text (hash: {text_hash[:16]}...)")
		except Exception as e:
			logger.warning(f"[NLP-Cache] Failed to clear cache: {e}")
	else:
		logger.info(f"[NLP-Cache] Checking cache for text (hash: {text_hash[:16]}... | preview: \"{text_preview}...\")")
	
	# Try to get from cache first (unless force_refresh is True)
	if not force_refresh:
		try:
			redis_client = get_redis()
			cached = redis_client.get(cache_key)
			if cached:
				logger.info(f"[NLP-Cache] ✅ CACHE HIT - Using cached data (hash: {text_hash[:16]}... | preview: \"{text_preview}...\")")
				logger.info(f"[NLP-Cache] ⚡ Skipping LLM call - returning cached result (saved cost & latency)")
				cached_data = json.loads(cached)
				result = NLPResponse(**cached_data)
				logger.info(f"[NLP-Cache] Cached result: Phones={len(result.phones)}, Amounts={len(result.amounts)}, "
				           f"ClientNames={len(result.client_names)}, JobTypes={len(result.job_types)}")
				return result
			else:
				logger.info(f"[NLP-Cache] ❌ CACHE MISS - No cached data found (hash: {text_hash[:16]}... | preview: \"{text_preview}...\")")
				logger.info(f"[NLP-Cache] 🔄 This is a NEW voice note - will fetch fresh data from LLM")
		except Exception as e:
			logger.warning(f"[NLP-Cache] Redis error (continuing without cache): {e}")
			logger.info(f"[NLP-Cache] ⚠️  Cache unavailable - will proceed with fresh LLM fetch")
	
	# Try LLM first if API key is configured
	logger.info(f"[NLP-Cache] 🚀 Making NEW LLM API call for text (hash: {text_hash[:16]}... | preview: \"{text_preview}...\")")
	llm_result = _extract_entities_with_llm(text, region)
	
	if llm_result is not None:
		# Cache the LLM result for 24 hours (86400 seconds)
		# This ensures identical voice notes don't trigger duplicate LLM calls
		# Different voice notes will have different hashes and will fetch fresh data
		cache_ttl = 86400  # 24 hours
		try:
			redis_client = get_redis()
			cache_data = {
				"phones": llm_result.phones,
				"amounts": llm_result.amounts,
				"dates": llm_result.dates,
				"parts": llm_result.parts,
				"job_types": llm_result.job_types,
				"locations": llm_result.locations,
				"client_names": llm_result.client_names,
				"expenses": llm_result.expenses,
				"earnings": llm_result.earnings,
				"projected_expenses": llm_result.projected_expenses,
				"projected_earnings": llm_result.projected_earnings,
				"reminders": llm_result.reminders,
				"shopping_items": llm_result.shopping_items,
			}
			redis_client.setex(cache_key, cache_ttl, json.dumps(cache_data))
			logger.info(f"[NLP-Cache] 💾 Cached NEW LLM result (hash: {text_hash[:16]}... | TTL: {cache_ttl}s / 24h | preview: \"{text_preview}...\")")
			logger.info(f"[NLP-Cache] ✅ Future identical voice notes will use cache (saves cost & latency)")
		except Exception as e:
			logger.warning(f"[NLP-Cache] Failed to cache result: {e}")
		
		return llm_result
	
	# Fallback to regex-based extraction
	logger.info(f"[NLP-Regex] ⚠️  LLM not available, using regex-based extraction (hash: {text_hash[:16]}... | preview: \"{text_preview}...\")")
	
	phones = _extract_phones(text, region)
	amounts = _extract_amounts(text)
	dates = _extract_dates(text)
	parts = _extract_parts(text)
	job_types = _extract_job_types(text)
	locations = _extract_locations(text)
	client_names = _extract_client_names(text)
	
	logger.info(
		f"[NLP-Regex] Extracted entities - "
		f"Phones: {phones} | "
		f"Amounts: {amounts} | "
		f"Dates: {dates} | "
		f"Parts: {parts} | "
		f"Job Types: {job_types} | "
		f"Locations: {locations} | "
		f"Client Names: {client_names}"
	)
	
	result = NLPResponse(
		phones=phones,
		amounts=amounts,
		dates=dates,
		parts=parts,
		job_types=job_types,
		locations=locations,
		client_names=client_names,
		expenses=[],  # Regex fallback doesn't extract expenses/earnings/reminders
		earnings=[],
		projected_expenses=[],
		projected_earnings=[],
		reminders=[],
		shopping_items=[],
	)
	
	# Cache regex result too (1 hour TTL - 3600 seconds)
	cache_ttl = 3600  # 1 hour
	try:
		redis_client = get_redis()
		cache_data = {
			"phones": result.phones,
			"amounts": result.amounts,
			"dates": result.dates,
			"parts": result.parts,
			"job_types": result.job_types,
			"locations": result.locations,
			"client_names": result.client_names,
			"expenses": result.expenses,
			"earnings": result.earnings,
			"projected_expenses": result.projected_expenses,
			"projected_earnings": result.projected_earnings,
			"reminders": result.reminders,
			"shopping_items": result.shopping_items,
		}
		redis_client.setex(cache_key, cache_ttl, json.dumps(cache_data))
		logger.info(f"[NLP-Cache] 💾 Cached regex result (hash: {text_hash[:16]}... | TTL: {cache_ttl}s / 1h | preview: \"{text_preview}...\")")
	except Exception as e:
		logger.warning(f"[NLP-Cache] Failed to cache regex result: {e}")
	
	return result


@router.post("/tag", response_model=NLPResponse)
async def tag_entities(
	payload: NLPRequest,
	force_refresh: bool = Query(False, description="Force fresh extraction, bypass cache"),
	current_user: User = Depends(get_current_user)
):
	"""Extract entities from text. Uses LLM if available, falls back to regex."""
	logger.info(f"[NLP] 📝 Received entity extraction request (text length: {len(payload.text)} chars, force_refresh={force_refresh})")
	logger.info(f"[NLP] 📄 Text preview: \"{payload.text[:150].replace(chr(10), ' ')}...\"")
	return extract_entities(payload.text, payload.region or "KE", force_refresh=force_refresh)


@router.delete("/cache", status_code=status.HTTP_200_OK)
async def clear_nlp_cache(
	text: Optional[str] = Query(None, description="Clear cache for specific text (will hash it)"),
	text_hash: Optional[str] = Query(None, description="Clear cache for specific hash (16+ characters)"),
	all: bool = Query(False, description="Clear ALL NLP cache (use with caution)"),
	current_user: User = Depends(get_current_user)
):
	"""
	Clear NLP cache for debugging purposes.
	Can clear cache for a specific text, a specific hash, or all NLP cache.
	"""
	try:
		redis_client = get_redis()
		cleared_count = 0
		
		if all:
			# Clear all NLP cache keys
			pattern = "nlp:extract:*"
			keys = redis_client.keys(pattern)
			if keys:
				cleared_count = redis_client.delete(*keys)
				logger.info(f"[NLP-Cache] 🗑️  Cleared ALL NLP cache: {cleared_count} keys deleted")
				return {
					"message": f"Cleared all NLP cache",
					"keys_deleted": cleared_count
				}
			else:
				logger.info(f"[NLP-Cache] ℹ️  No NLP cache keys found to clear")
				return {
					"message": "No NLP cache keys found",
					"keys_deleted": 0
				}
		
		elif text:
			# Clear cache for specific text
			text_hash = hashlib.sha256(f"{text}:KE".encode()).hexdigest()
			cache_key = f"nlp:extract:{text_hash}"
			if redis_client.exists(cache_key):
				redis_client.delete(cache_key)
				logger.info(f"[NLP-Cache] 🗑️  Cleared cache for text (hash: {text_hash[:16]}...)")
				return {
					"message": "Cache cleared for text",
					"text_hash": text_hash[:16] + "...",
					"keys_deleted": 1
				}
			else:
				logger.info(f"[NLP-Cache] ℹ️  No cache found for text (hash: {text_hash[:16]}...)")
				return {
					"message": "No cache found for text",
					"text_hash": text_hash[:16] + "...",
					"keys_deleted": 0
				}
		
		elif text_hash:
			# Clear cache for specific hash
			# Find all keys that start with this hash
			pattern = f"nlp:extract:{text_hash}*"
			keys = redis_client.keys(pattern)
			if keys:
				cleared_count = redis_client.delete(*keys)
				logger.info(f"[NLP-Cache] 🗑️  Cleared cache for hash: {text_hash[:16]}... ({cleared_count} keys)")
				return {
					"message": "Cache cleared for hash",
					"text_hash": text_hash[:16] + "...",
					"keys_deleted": cleared_count
				}
			else:
				logger.info(f"[NLP-Cache] ℹ️  No cache found for hash: {text_hash[:16]}...")
				return {
					"message": "No cache found for hash",
					"text_hash": text_hash[:16] + "...",
					"keys_deleted": 0
				}
		
		else:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="Must provide 'text', 'text_hash', or 'all=true' parameter"
			)
	
	except Exception as e:
		logger.error(f"[NLP-Cache] Error clearing cache: {e}", exc_info=True)
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Failed to clear cache: {str(e)}"
		)
