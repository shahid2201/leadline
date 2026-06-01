# Lead Line Backend - Phases 1 to 4

This repository contains the Phase 1 to Phase 4 foundation for Lead Line:

- FastAPI backend scaffold
- Multi-tenant auth middleware (API key or JWT)
- Tenant, user, and API key models
- Health endpoints
- Structured JSON logging
- Lead/session/message/timeline CRUD APIs
- Tenant-scoped deduplication rules for lead creation
- SQS queue publishing and worker skeleton
- AI orchestration (prompt versioning, model selection, OpenAI integration)
- Async message analysis pipeline for intent/entities/sentiment/urgency
- Initial lead scoring from AI understanding and engagement context
- Redis cache for idempotent AI results
- Routing rules CRUD and deterministic routing evaluation engine
- Sequence CRUD, step management, and enrollment APIs
- Worker-driven sequence execution with timeline recording
- SES and Twilio delivery integration adapters
- Docker local environment
- CI pipeline (lint + tests)

## Quick start

1. Copy environment file:

   cp .env.example .env

2. Start local stack:

   docker compose up --build

3. Open API docs:

   http://localhost:8000/docs

## Local development (without Docker)

1. Create a virtual environment.
2. Install dependencies:

   pip install -e .[dev]

3. Run the API:

   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

4. Run tests:

   pytest

## API auth behavior

- `Authorization: Bearer <token>` is required for non-health routes.
- If token looks like JWT (`x.y.z`), JWT auth is used.
- Otherwise token is treated as API key and validated against hashed storage.

## Health endpoints

- `GET /healthz` liveness probe
- `GET /readyz` readiness probe (checks DB)

## Phase 2 API groups

- Leads
   - `POST /v1/leads`
   - `GET /v1/leads`
   - `GET /v1/leads/{id}`
   - `PATCH /v1/leads/{id}`
   - `DELETE /v1/leads/{id}`
   - `GET /v1/leads/{id}/timeline`
   - `POST /v1/leads/{id}/timeline`
   - `POST /v1/leads/{id}/attach-session`

- Timeline
   - `GET /v1/timeline/{id}`
   - `PATCH /v1/timeline/{id}`
   - `DELETE /v1/timeline/{id}`

- Sessions and messages
   - `POST /v1/sessions`
   - `GET /v1/sessions`
   - `GET /v1/sessions/{id}`
   - `PATCH /v1/sessions/{id}`
   - `DELETE /v1/sessions/{id}`
   - `POST /v1/sessions/{id}/messages`
   - `GET /v1/sessions/{id}/messages`
   - `GET /v1/messages/{id}`
   - `PATCH /v1/messages/{id}`
   - `DELETE /v1/messages/{id}`

## Worker skeleton

Run worker process:

`python -m app.workers.main`

If SQS queue URLs are not configured, message publishing and worker polling become safe no-ops.

## Phase 3 AI processing

- Message-created queue events trigger async AI analysis in worker.
- AI orchestration supports:
   - Prompt templates with versioning (`AI_PROMPT_VERSION`)
   - Model routing (`OPENAI_MODEL_MINI` vs `OPENAI_MODEL_FULL`)
   - OpenAI-first with deterministic heuristic fallback
- AI output persists to message annotations:
   - `intent`, `entities`, `sentiment`, `urgency`, `topics`
- If the message is attached to a lead, initial scoring is computed:
   - `fit_score`, `engagement_score`, `lead_score`
- Results are cached in Redis by:
   - `(tenant_id, message_id, prompt_version, model)`

## Phase 4 routing and sequences

- Routing rules APIs:
   - `GET/POST/PATCH/DELETE /v1/routing/rules`
- Sequence APIs:
   - `GET/POST/PATCH/DELETE /v1/sequences`
   - `GET/POST/PATCH/DELETE /v1/sequences/{id}/steps`
   - `POST /v1/sequences/{id}/enroll`
- Lifecycle events (`lead.created`, `lead.updated`, `lead.score_updated`) trigger routing evaluation and sequence enrollment through worker queues.
- Routing actions supported:
   - `assign_user` -> `owner_user_id`
   - `assign_team` -> `assigned_team_id`
   - `queue` -> `assigned_queue_name`
- Sequence step execution supports `email`, `sms`, `wait`, and `task` types.
- Delivery integrations:
   - Amazon SES for email (`SES_FROM_EMAIL`)
   - Twilio for SMS (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_PHONE`)
