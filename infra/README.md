# Infra quickstart

## Prerequisites
- Docker + Docker Compose

## Start services
```bash
cd infra
docker compose up -d --build
```
Services:
- Postgres: localhost:5432 (user/pass/db: app/app/app)
- Redis: localhost:6379
- MinIO: S3 on :9000, console on :9001 (minioadmin/minioadmin)
- Backend API: http://localhost:8000 (after backend build)
- Worker: background jobs

## Environment
- Copy `backend/env.sample` to `backend/.env` for local dev.

## Migrations (Alembic)
```bash
cd backend
alembic -c alembic.ini upgrade head
```
- To create a new revision after model changes:
```bash
alembic -c alembic.ini revision --autogenerate -m "describe change"
alembic -c alembic.ini upgrade head
```

## Health check
- After up: `curl http://localhost:8000/healthz` → `{ "status": "ok" }`

## Reset local DB (DANGEROUS)
```bash
cd infra
docker compose down -v && docker compose up -d --build
```
