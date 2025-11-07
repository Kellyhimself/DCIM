## MVP Spec: AI "Second Brain" for Blue‑Collar Workers (Kenya‑first)

### Goal
- Capture voice notes on‑site → bilingual transcripts → auto‑link to jobs/clients/parts → fast recall and simple share‑outs.

### Primary users
- Plumbers, electricians, drivers, fundis, small contractors (owner + 2–10 crew).

### Core jobs (must‑have)
- Speak a note; see transcript in <30s even when offline (queued).
- Auto‑tag: client, job/site, parts, dates, money, next steps.
- Auto-suggestions / reminders generated(missing  )
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

---

## Phase 2: Marketplace + Social Platform (Future Vision)

### Vision
Transform Second Brain from a productivity tool into a complete ecosystem connecting blue‑collar workers with customers, while building a vibrant community around the jua kali economy. Workers who already trust Second Brain for their daily operations can seamlessly discover new clients, showcase their work, and grow their businesses.

### Strategic rationale
- **Bootstrap advantage**: Existing Second Brain users become the initial supply side (workers) with established trust and daily engagement
- **Lower customer acquisition cost**: Workers bring their existing clients into the platform organically
- **Data moat**: Job history, ratings, and work portfolios from Second Brain create trust signals unavailable to pure marketplace competitors
- **Network effects**: More workers → more customers → more jobs → more value for everyone

### Core marketplace features

#### For workers (supply side)
- **Public profile**: Auto‑generated from Second Brain data (trade, location, years of experience, portfolio photos from job notes)
- **Service listings**: Create service offerings (e.g., "Plumbing repairs", "Electrical installations") with pricing ranges, availability, service areas
- **Job discovery**: Browse customer requests; apply or accept jobs based on location, trade match, and customer ratings
- **Portfolio showcase**: Auto‑curated gallery from completed job photos/notes (with permission); before/after comparisons
- **Verified badges**: Earn verification through completed jobs, customer ratings, and Second Brain usage history
- **Availability calendar**: Set working hours, mark busy days, auto‑update from scheduled jobs in Second Brain

#### For customers (demand side)
- **Request a service**: Post job requests with photos, description, location, urgency, budget range
- **Browse workers**: Search by trade, location, ratings, price range; filter by verified, available now, portfolio quality
- **Compare quotes**: Receive multiple quotes from workers; compare based on price, ratings, portfolio, response time
- **In‑app messaging**: Chat with workers before/after job acceptance; share photos, location pins, voice messages
- **Job tracking**: See job status updates (accepted → in progress → completed) synced from Second Brain
- **Reviews & ratings**: Rate completed jobs; reviews auto‑populate from Second Brain job completion data

#### Marketplace mechanics
- **Matching algorithm**: Location‑based + trade dictionary matching + availability + ratings + response time
- **Escrow payments**: Hold payment until job completion; release via M‑Pesa on customer approval
- **Dispute resolution**: Built‑in mediation flow; leverage Second Brain job notes/photos as evidence
- **Transaction fees**: 5–8% commission on completed jobs (lower than competitors due to existing infrastructure)
- **Insurance integration**: Optional job insurance for high‑value work; partnerships with micro‑insurers

### Social media features

#### Community feed
- **Work showcase**: Workers share completed projects (photos, brief descriptions); customers can save/favorite
- **Tips & tricks**: Trade‑specific tips, tool recommendations, troubleshooting guides
- **Success stories**: Feature workers who've grown their business using the platform
- **Local events**: Promote trade shows, training workshops, tool exhibitions
- **Q&A forum**: Ask questions, get answers from experienced workers; upvote helpful responses

#### Social connections
- **Follow workers**: Customers follow favorite workers; get notified of new portfolio posts, availability
- **Worker networks**: Workers connect with others in their trade; share referrals, collaborate on large jobs
- **Groups**: Location‑based or trade‑based groups (e.g., "Nairobi Electricians", "Mombasa Plumbers")
- **Messaging**: Direct messages between users; group chats for teams/customers

#### Content creation
- **Video tutorials**: Short how‑to videos from workers (e.g., "How to fix a leaking tap")
- **Before/after posts**: Visual transformations with brief captions
- **Tool reviews**: Workers review tools/equipment; customers can ask questions
- **Live updates**: Workers post real‑time job progress (with customer permission)

### Integration with Second Brain

#### Seamless data flow
- **Auto‑portfolio**: Completed jobs in Second Brain automatically populate worker portfolio (opt‑in)
- **Job sync**: Marketplace jobs automatically create Second Brain job records; notes/photos sync back to marketplace
- **Rating import**: Customer ratings from marketplace appear in Second Brain client records
- **Invoice sharing**: Marketplace customers can view invoices generated in Second Brain
- **Availability sync**: Calendar in Second Brain updates marketplace availability

#### Unified experience
- **Single app**: Marketplace and Second Brain features in one app; toggle between "Work" and "Find Jobs" modes
- **Shared authentication**: Same login; marketplace profile linked to Second Brain account
- **Cross‑promotion**: Second Brain users see marketplace opportunities; marketplace workers encouraged to use Second Brain for job management

### Enhanced data model (Phase 2)

```
User {
  ...existing fields...
  marketplaceProfile: MarketplaceProfile
  socialProfile: SocialProfile
}

MarketplaceProfile {
  userId, trade, serviceAreas[], hourlyRate?, fixedRates{}, 
  availability, verified, rating, completedJobsCount, 
  portfolioPhotos[], serviceListings[], bio, languages[]
}

ServiceListing {
  workerId, title, description, trade, priceRange, 
  serviceAreas[], photos[], createdAt
}

JobRequest {
  customerId, title, description, trade, location, 
  urgency, budgetRange, photos[], status, createdAt
}

Quote {
  jobRequestId, workerId, amount, message, 
  estimatedDuration, status (pending/accepted/rejected)
}

Transaction {
  quoteId, customerId, workerId, amount, 
  escrowStatus, paymentStatus, completedAt
}

Review {
  transactionId, reviewerId, revieweeId, rating, 
  comment, photos[], createdAt
}

SocialPost {
  authorId, type (showcase/tip/story), content, 
  photos[], videos[], likes[], comments[], createdAt
}

Follow {
  followerId, followingId, createdAt
}

Group {
  name, description, type (location/trade), 
  members[], posts[], createdAt
}
```

### Revenue model (Phase 2)

#### Primary revenue streams
1. **Transaction commissions**: 5–8% of completed job value (lower than 10–15% typical due to existing infrastructure)
2. **Premium listings**: Workers pay KES 500–2,000/month for featured placement, priority in search
3. **Subscription tiers**: 
   - Marketplace Basic: Free (limited listings, basic profile)
   - Marketplace Pro: KES 1,500/month (unlimited listings, analytics, priority support)
   - Combined (Second Brain + Marketplace): KES 2,000/month (discounted bundle)
4. **Advertising**: Sponsored posts, tool/equipment supplier ads, training course promotions
5. **Payment processing**: Small fee on M‑Pesa transactions (1–2%)

#### Pricing strategy
- **Workers**: Free to join; commission only on completed jobs; optional premium features
- **Customers**: Free to post requests and browse; pay only for completed work
- **Value proposition**: Lower fees than competitors due to existing Second Brain infrastructure

### Success metrics (Phase 2)

#### Marketplace health
- **Supply**: ≥500 active workers (from Second Brain user base) within 3 months
- **Demand**: ≥2,000 customer signups within 3 months
- **Liquidity**: ≥50 completed jobs/month by month 3; ≥200/month by month 6
- **Match rate**: ≥60% of job requests receive at least 2 quotes within 24 hours
- **Completion rate**: ≥80% of accepted quotes result in completed transactions

#### Engagement
- **Social**: ≥30% of users engage with feed (like/comment/share) weekly
- **Content**: ≥100 posts/week from workers by month 3
- **Retention**: ≥40% of marketplace users return monthly
- **Cross‑usage**: ≥70% of marketplace workers also use Second Brain features

#### Financial
- **GMV**: ≥KES 2M in completed job value by month 6
- **Revenue**: ≥KES 100K/month from commissions by month 6
- **Unit economics**: CAC < LTV/3; positive contribution margin per transaction

### Technical requirements (Phase 2)

#### New infrastructure
- **Real‑time features**: WebSocket server for messaging, live job updates, notifications
- **Search & discovery**: Elasticsearch or Algolia for advanced worker/job search with filters
- **Image processing**: Thumbnail generation, compression, CDN for portfolio photos
- **Push notifications**: Firebase Cloud Messaging for job matches, messages, reviews
- **Maps integration**: Google Maps/Mapbox for location‑based search, service area visualization
- **Payment gateway**: Enhanced M‑Pesa integration for escrow, multi‑party payments

#### Scalability considerations
- **Database**: Read replicas for search queries; caching layer (Redis) for hot data
- **Media storage**: CDN for photos/videos; separate bucket for user‑generated content
- **Background jobs**: Queue system for notifications, email/SMS, analytics aggregation
- **Monitoring**: Enhanced observability for marketplace transactions, fraud detection

### Development roadmap (Phase 2)

#### Month 1–2: Foundation
- Extend data models for marketplace entities
- Build worker profile creation/editing (auto‑populate from Second Brain)
- Implement basic job request posting and browsing
- Location‑based search and filtering

#### Month 3–4: Core marketplace
- Quote system (workers submit quotes, customers compare)
- Escrow payment flow (M‑Pesa integration)
- Job acceptance and status tracking
- Basic rating/review system
- Integration with Second Brain job sync

#### Month 5–6: Social features
- Community feed (showcase posts, tips)
- Follow/follower system
- In‑app messaging
- Groups (location/trade‑based)
- Content creation tools (photo posts, short videos)

#### Month 7–8: Polish & scale
- Advanced matching algorithm
- Dispute resolution flow
- Analytics dashboard for workers
- Premium features (featured listings, analytics)
- Marketing tools (referral program, promotions)

### Risks & mitigations (Phase 2)

#### Chicken‑and‑egg problem
- **Risk**: Need both workers and customers simultaneously
- **Mitigation**: Start with Second Brain users as supply; incentivize them to bring customers; run targeted customer acquisition campaigns in high‑demand areas

#### Trust & safety
- **Risk**: Fraud, poor work quality, disputes
- **Mitigation**: Verification badges, escrow payments, review system, dispute mediation, leverage Second Brain job history as trust signal

#### Competition
- **Risk**: Established players (Facebook groups, Jumia Services, local competitors)
- **Mitigation**: Differentiate through Second Brain integration, lower fees, better UX, focus on specific trades initially

#### Unit economics
- **Risk**: High customer acquisition cost, low transaction frequency
- **Mitigation**: Leverage Second Brain user base, focus on repeat customers, bundle subscriptions, optimize matching to increase completion rates

### Success criteria for Phase 2 launch
- Second Brain has ≥200 active paying users (validates demand and provides initial supply)
- Pilot marketplace with 50 workers and 200 customers shows ≥60% match rate
- ≥10 completed transactions with positive reviews in pilot
- Technical infrastructure handles 100 concurrent users without degradation
- Unit economics validated: commission revenue > customer acquisition cost

### Long‑term vision (Phase 3+)
- **Financial services**: Micro‑loans for tools/equipment based on job history and ratings
- **Training platform**: Online courses, certifications, skill development
- **Supply chain**: Connect workers with tool/part suppliers; bulk purchasing discounts
- **Insurance products**: Job insurance, equipment insurance, health insurance for workers
- **Expansion**: Replicate model in other African markets (Tanzania, Uganda, Rwanda)

## Phase 3: AI llm:
🗣️ (A) Improve Understanding with Fine-tuned NLP Models

Instead of regex + keyword detection, train or prompt-tune an LLM (like GPT-4o-mini or a smaller local model) to understand unstructured speech.

Example:

“Today I fixed a leaking sink for Mama Akinyi, charged her 1,200, will return Monday.”

A simple prompt could produce structured JSON:

{
  "client": "Mama Akinyi",
  "job_type": "Plumbing",
  "amount": 1200,
  "return_date": "Monday",
  "action": "Follow-up"
}


You can test this using an LLM function-calling schema in your FastAPI backend:

Send transcript → model returns structured JSON.

Much smarter than regex (handles flexible language and mixed Swahili-English).

🧩 (B) Context Memory — The Worker’s “Knowledge Graph”

Store each extracted entity (client, job, materials, cost) as nodes in a graph:

Worker → Job → Client → Material

Job → Notes

Job → Date

This lets you later query relationships:

“What jobs did I do for Mama Akinyi this year?”
“How much did I earn from plumbing last month?”

That’s contextual AI memory — it’s how your “second brain” gets its intelligence.

🧠 (C) Semantic Search (Vector Embeddings)

Don’t just use keyword search; use vector embeddings to find meaning-based results.

Example:

User searches: “repair for the pipe that burst”

You return notes mentioning “leak,” “pipe,” or “water fix,” even if “burst” wasn’t said.

Implementation:

Generate embeddings for each transcript using text-embedding-3-small.

Store in Postgres (via pgvector) or a vector DB (like Qdrant).

When the user searches → embed query → cosine similarity → return most relevant notes.

🔄 (D) AI Summarization and Smart Recall

Later, you can use an LLM to summarize or analyze a worker’s history.

Example:

“Summarize what I did for Mama Akinyi last month.”

→ Model returns:

“You replaced a sink pipe, installed a new tap, and followed up for leaks. Total earnings: KES 2,700.”

That’s retrieval + summarization, which makes your product feel like a true assistant.

⏰ (E) Smart Assistive Actions

Once AI extracts intent, you can act on it:

Intent	Action
“Will return Monday”	Create reminder
“Need to buy 3 elbows”	Add to shopping list
“Paid 1,200 by cash”	Update earnings summary
“Call client tomorrow”	Add to to-do list

These are rule-driven, but the trigger detection can be handled by an LLM or classifier trained on your transcripts.

⚒️ 4. How It Becomes “AI for the Informal Economy”

Let’s zoom out — what you’re doing isn’t just transcription.
You’re building an AI productivity layer for millions of workers who:

work verbally,

don’t use formal project management tools,

live in a multilingual reality.

Your AI:

Listens like an assistant

Understands context

Acts on it automatically

This means a mason, boda driver, or mechanic can organize their entire work life through speech.

That’s a category-defining idea — exactly the kind of “AI-for-good” investors love.