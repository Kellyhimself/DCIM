from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.settings import settings
from backend.app.routers import auth as auth_router
from backend.app.routers import clients as clients_router
from backend.app.routers import jobs as jobs_router
from backend.app.routers import notes as notes_router
from backend.app.routers import search as search_router
from backend.app.routers import nlp as nlp_router
from backend.app.routers import billing as billing_router
from backend.app.routers import teams as teams_router

app = FastAPI(title="Second Brain API", version="0.1.0")

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
