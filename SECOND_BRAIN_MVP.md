## MVP Spec: AI "Second Brain" for Blue‑Collar Workers (Kenya‑first)

### Goal
- Capture voice notes on‑site → bilingual transcripts → auto‑link to jobs/clients/parts → fast recall and simple share‑outs.

### Primary users
- Plumbers, electricians, drivers, fundis, small contractors (owner + 2–10 crew).

### Core jobs (must‑have)
- Speak a note; see transcript in <30s even when offline (queued).
- Auto‑tag: client, job/site, parts, dates, money, next steps.
- Search: by name, site, part, phone number, date.
- Share: WhatsApp summary to client/foreman; 1‑click PDF job card/invoice.
- Team: assign note to a crew member; simple status (pending/done).

### MVP scope (6–8 weeks)
- Voice capture: push‑to‑talk; attach photos; low‑bandwidth mode.
- Transcription: Swahili/English mix; cloud first (Whisper API), fallback queue.
- NLP tagging: regex + light NER for names/phones/amounts; trade dictionary.
- Entities: Clients, Jobs, Notes, Parts (tags), Team members.
- Search: full‑text + filters; recent items offline.
- Exports: job PDF (logo, client, tasks, parts, totals); CSV export.
- Sharing: WhatsApp text summary; optional link view.
- Billing: M‑Pesa Daraja subscription; 14‑day trial; usage cap alert.
- Admin: add team, set default trade terms, logo, company details.
- Privacy: device PIN/biometric lock; local encryption at rest; data retention (90 days default).

### Non‑goals (v1)
- Deep inventory integrations, complex scheduling, GPS tracking, advanced analytics, multi‑tenant hierarchies.

### User journeys
- Capture: Open app → hold to record → auto‑tag preview → Save → Share to WhatsApp.
- Recall: Search "Wanjiru P‑trap" → open job → see notes, photos, totals.
- Handover: Mark note "done" or assign to "Moses"; due today.
- Invoice: Tap "Create invoice" from job → edit line items → PDF → WhatsApp/email.

### Screens (Flutter)
- Home (recent notes/jobs + record button)
- Record (waveform, pause, attach photo, save)
- Note detail (transcript, tags, assign, share)
- Job detail (client, site, notes, parts, totals, PDF)
- Search (global search + filters)
- Team & Settings (members, company, billing)

### Data model (minimal)
- User, Team
- Client {name, phone, location}
- Job {clientId, site, status, createdAt}
- Note {jobId?, clientId?, text, audioUri, photos[], tags[], assigneeId?, createdAt}
- Tag {type: person | part | location | date | money}
- Invoice {jobId, items[], totals, pdfUrl}

### Tech choices
- App: Flutter; local DB via `sqflite` or `Drift` for offline-first; background sync with `workmanager`.
- Backend: FastAPI + Postgres (SQLAlchemy + Alembic), Auth via JWT (access/refresh), Object storage S3/Backblaze for media; optional Redis for jobs/queues.
- STT: Start with Whisper API; explore on‑device via `whisper.cpp` (FFI) for pro/offline users.
- NLP: FastAPI workers (regex + embeddings) with trade dictionaries.
- Vector search: Postgres pgvector or a lightweight service; cache recent items on device.
- Payments: M‑Pesa Daraja (STK push), usage metering in Postgres.
- Messaging: WhatsApp share sheet; later WhatsApp Cloud API integration.

### AI specifics (v1 heuristics)
- Regex: phones, amounts, dates, verbs (replace/install/fix) and quantities.
- Dictionary: common parts per trade (P‑trap, U‑bend, MCB, socket, gland, etc.).
- Entity linking: if client name/phone seen, auto‑link; else suggest create.
- Confidence thresholds; quick correction chips on note detail.

### Performance targets
- Record → visible transcript: <30s on 3G; offline queue save <2s.
- Search list render: <200ms from local cache.
- App size: <50 MB (no heavy on‑device STT in base build).

### Security & privacy
- Biometric/app PIN; encrypted local DB (use platform support/libs).
- Media stored locally; upload only on Wi‑Fi by default (toggle).
- Team roles: owner, member (no billing access).

### Pricing (launch)
- Free trial 14 days; Starter KES 800/user/mo; Team KES 3,500/5 users/mo.
- Add‑ons: extra transcription hours; branded PDFs.

### Success metrics (pilot)
- DAU ≥ 50% of invited users.
- ≥3 notes/user/day; median transcript turnaround <30s.
- ≥70% of users share to WhatsApp at least once in week 1.
- ≥30% convert to paid after trial via M‑Pesa.

### 2‑week pilot plan
- Week 1: Build capture, cloud STT, basic tagging, jobs/clients, search, WhatsApp share, local DB, FastAPI+Postgres backend skeleton.
- Week 2: PDFs, M‑Pesa trial billing, team/assign, offline queue polish, trade dictionaries, field tests with 10 crews (3 trades).

### Optional kit (bill of materials)
- Budget Android (2–4 GB RAM), lapel mic, power bank; optional tripod/phone mount.

### Top risks + mitigations
- Latency/cost of STT → compress audio, queue, on‑device for heavy users.
- Bilingual accuracy → custom prompts + trade dictionary + user correction chips.
- Adoption → WhatsApp‑first share, minimal fields, field onboarding scripts.

### Development plan (14 days)

- Day 1: Repo + CI/CD skeleton
  - Create monorepo structure: `mobile/`, `backend/`, `worker/`, `infra/`.
  - Backend scaffold (FastAPI, SQLAlchemy, Alembic, JWT auth, pydantic models).
  - Postgres + Redis + MinIO/S3 via Docker Compose; health checks.
  - Flutter app init; env config, flavors, base navigation/shell.
  - Deliverables: running `docker compose up`; mobile app boots to Home.
  - Acceptance: CI runs lint/tests; backend `/healthz` returns 200.

- Day 2: Auth, users, teams
  - Backend: users, teams, roles, JWT (access/refresh), password reset.
  - Mobile: email/phone login screen, secure storage of tokens.
  - Deliverables: Sign up/in/out; whoami endpoint; protected route.
  - Acceptance: E2E happy path on device + Postman collection passes.

- Day 3: Entities (clients, jobs)
  - Backend CRUD + migrations; simple validation; list/filter endpoints.
  - Mobile: local models, repository pattern, basic create/list/edit screens.
  - Deliverables: Create client, create job linked to client.
  - Acceptance: Data persists in Postgres and shows in app lists.

- Day 4: Notes capture (audio + photos)
  - Mobile: push‑to‑talk, file storage, attach photos, offline save queue.
  - Backend: pre‑signed upload URLs to S3; media metadata model.
  - Deliverables: Record audio, attach 1 photo, save note locally and sync.
  - Acceptance: Files stored; note record created with media links.

- Day 5: Cloud STT pipeline
  - Worker: job queue (RQ/Arq), STT job consumes S3 audio, calls Whisper API.
  - Backend: webhook/callback or polling; note transcript field updates.
  - Deliverables: Note → transcript within 30s for 1‑2 min audio.
  - Acceptance: Latency p50 < 30s in test; retries on failure.

- Day 6: Tagging + dictionaries
  - Backend NLP: regex for phones, dates, amounts; trade dictionary lookup.
  - Mobile: highlight chips, quick corrections, link to client/job if matched.
  - Deliverables: Auto‑tags visible; manual correction updates server.
  - Acceptance: ≥80% precision on phones/amounts in test set.

- Day 7: Search
  - Backend: text search endpoints (ILIKE + trigram); optional pgvector later.
  - Mobile: global search screen with filters (client, job, date, part tag).
  - Deliverables: Search by client name and part returns expected notes/jobs.
  - Acceptance: Query returns <300ms server‑side on dev data set.

- Day 8: Share + PDF job card
  - Backend: simple PDF generation (WeasyPrint/ReportLab); store in S3.
  - Mobile: WhatsApp share sheet; link + PDF attachment.
  - Deliverables: Generate PDF from job; share to WhatsApp.
  - Acceptance: PDF < 300 KB, renders on phone; share flow works offline (queued).

- Day 9: Billing (M‑Pesa trial)
  - Backend: Daraja STK push integration; plans, usage metering, webhooks.
  - Mobile: billing page, trial countdown, “Go Pro” button.
  - Deliverables: Test Paybill/Till sandbox end‑to‑end.
  - Acceptance: Webhook recorded; plan assigned; access gated post‑trial.

- Day 10: Offline sync polish
  - Mobile: background sync with `workmanager`; conflict resolution.
  - Backend: pagination, ETags/If‑Modified‑Since; basic rate limiting.
  - Deliverables: Airplane mode capture → auto sync on reconnect.
  - Acceptance: No data loss in repeated toggle tests; duplicates avoided.

- Day 11: Stability + error handling
  - Add Sentry/Crashlytics, structured logging, retries/backoff.
  - QA pass for network/power interruptions; large audio handling.
  - Deliverables: Error toasts, retry UI, logs with correlation IDs.
  - Acceptance: 0 critical crashes in 1‑hour soak test.

- Day 12: UX polish + localization
  - Copy tweaks, Swahili/English labels; onboarding screens and empty states.
  - Deliverables: Onboarding checklist; contextual tips.
  - Acceptance: First‑time user can create client, job, note without guidance.

- Day 13: Field pilot setup
  - Seed trade dictionaries; preload sample clients; create feedback channel.
  - Train 5–10 pilot users; instrument analytics (Amplitude/Mixpanel).
  - Deliverables: Pilot cohort onboarded; baseline metrics dashboard.
  - Acceptance: DAU ≥ 50% on day 1 of pilot, telemetry flowing.

- Day 14: Iterate + release beta
  - Fix top pilot issues; prepare beta build; write quickstart and FAQ.
  - Deliverables: Beta APK/IPA (internal), release notes.
  - Acceptance: All P1 bugs resolved; sign‑off to expand pilot.

### Roles & tooling
- Roles: Mobile dev, Backend/API, Infra/DevOps, QA/Field.
- Tooling: GitHub Actions CI, Docker Compose dev, Black/Flake8/Mypy, Dart analyze, Prettier for JSON/YAML.

### Definition of done (MVP)
- A user can: record a note, auto‑tag/link it to a client/job, search and find it, generate and share a PDF/job summary, and start a paid trial via M‑Pesa. Median transcript latency <30s on 3G; offline capture works reliably.
