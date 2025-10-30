# Second Brain (MVP)

## Quickstart
1. Copy environment
```bash
cp backend/env.sample backend/.env
```

2. Run infra + backend + worker
```bash
cd infra
docker compose up -d --build
```
- API: http://localhost:8000/healthz
- MinIO console: http://localhost:9001 (minioadmin/minioadmin)

3. Mobile (Flutter)
- See `mobile/README.md` for packages and API base URL.
- Point base URL to your machine IP if testing on a physical device.

## Storage
- Local dev: uses MinIO via Docker (S3-compatible). Values are in `backend/.env`.
- Staging/Prod: use Cloudflare R2 (S3-compatible). Set in `backend/.env`:
  - `S3_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
  - `S3_BUCKET=<your-bucket>`
  - `S3_ACCESS_KEY=<r2-access-key-id>`
  - `S3_SECRET_KEY=<r2-secret-access-key>`

## Structure
- `backend/` FastAPI app
- `worker/` Background jobs (STT queue stub)
- `infra/` Docker Compose, Dockerfiles
- `mobile/` Flutter app (to be created)

## Next
- Implement auth routes and basic CRUD for clients/jobs/notes per `SECOND_BRAIN_MVP.md`.
