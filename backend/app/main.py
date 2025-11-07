from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import json
import time

from backend.app.settings import settings
from backend.app.routers import auth as auth_router
from backend.app.routers import clients as clients_router
from backend.app.routers import jobs as jobs_router
from backend.app.routers import notes as notes_router
from backend.app.routers import search as search_router
from backend.app.routers import nlp as nlp_router
from backend.app.routers import billing as billing_router
from backend.app.routers import teams as teams_router

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Second Brain API", version="0.1.0")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
	"""Middleware to log incoming requests with body for POST/PUT requests."""
	
	async def dispatch(self, request: Request, call_next):
		start_time = time.time()
		
		# Read request body if it's a POST/PUT/PATCH request
		body = None
		body_bytes = b""
		if request.method in ["POST", "PUT", "PATCH"]:
			body_bytes = await request.body()
			if body_bytes:
				try:
					body = json.loads(body_bytes.decode('utf-8'))
				except (json.JSONDecodeError, UnicodeDecodeError):
					body = body_bytes[:500].decode('utf-8', errors='replace')  # Truncate and decode
		
		# Log request
		logger.info(
			f"Request: {request.method} {request.url.path} | "
			f"Query: {dict(request.query_params)} | "
			f"Body: {json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else body}"
		)
		
		# Recreate request with body (since we consumed it)
		if body_bytes:
			async def receive():
				return {"type": "http.request", "body": body_bytes}
			request._receive = receive
		
		# Process request
		response = await call_next(request)
		
		# Log response
		process_time = time.time() - start_time
		logger.info(
			f"Response: {request.method} {request.url.path} | "
			f"Status: {response.status_code} | "
			f"Time: {process_time:.3f}s"
		)
		
		return response


app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(clients_router.router)
app.include_router(jobs_router.router)
app.include_router(notes_router.router)
app.include_router(search_router.router)
app.include_router(nlp_router.router)
app.include_router(billing_router.router)
app.include_router(teams_router.router)


@app.get("/healthz")
async def healthz():
	return {"status": "ok", "env": settings.environment}

@app.get("/debug/s3")
async def debug_s3():
	"""Debug endpoint to check S3 settings (remove in production)"""
	return {
		"s3_endpoint": settings.s3_endpoint,
		"s3_public_endpoint": settings.s3_public_endpoint,
		"s3_bucket": settings.s3_bucket,
	}