# Lead Line Backend - Phases 1 to 7

This repository contains the Phase 1 to Phase 7 foundation for Lead Line:

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
- HubSpot lead/activity sync integration hooks
- Google Calendar availability and booking APIs
- Slack high-intent lead alert integration hooks
- Svix outbound webhooks and inbound webhook endpoints
- Webhook signature verification and idempotency event store
- OpenTelemetry tracing across API, DB, worker, AI, and integrations
- Prometheus metrics endpoint, Grafana dashboard, and alert rules
- RBAC enforcement, tenant-aware rate limiting, and tenant header checks
- Audit logs and PII masking controls for request/security events
- Encryption controls for persisted integration auth payloads
- Outage runbooks for AI, messaging, and database degradation
- Tenant provisioning workflow and design-partner rollout controls
- Plan limit enforcement for leads, sessions, and messages
- Layered launch test matrix: unit, integration, contract, e2e, AI regression
- Staging soak test tooling and rollback/on-call readiness docs
- Docker local environment
- CI pipeline with quality gates and layered test jobs

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

5. Run full launch test layers:

   python scripts/run_test_layers.py

6. Export OpenAPI contract artifact:

   python scripts/export_openapi.py

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

## Phase 5 integrations and webhooks

- Integration APIs:
   - `POST /v1/integrations/hubspot/leads/{id}/sync`
   - `GET /v1/integrations/calendar/availability`
   - `POST /v1/integrations/calendar/bookings`
- Inbound webhook APIs:
   - `POST /v1/webhooks/svix`
   - `POST /v1/webhooks/hubspot`
- Integration worker events:
   - `integration.lead.created`
   - `integration.lead.updated`
   - `integration.lead.score_updated`
   - `integration.timeline.created`
- Webhook processing stores provider events with idempotency keys and retry status.

## Phase 6 observability and security hardening

- Metrics endpoint:
   - `GET /metrics`
- OpenTelemetry:
   - Configured via `OTEL_ENABLED`, `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`
   - Request, queue, AI, DB, worker, and integration spans are emitted
- Security controls:
   - RBAC admin enforcement on routing/sequences/integrations APIs
   - Tenant-aware rate limiting (`RATE_LIMIT_PER_MINUTE`)
   - Tenant header mismatch blocking (`ENFORCE_TENANT_HEADER_MATCH`)
   - Audit log persistence in `audit_logs`
   - PII masking for logged/audited metadata
   - Integration auth payload encryption when `APP_DATA_ENCRYPTION_KEY` is set
- Dashboards and alerts:
   - Prometheus config: `observability/prometheus/prometheus.yml`
   - Alert rules: `observability/prometheus/alert_rules.yml`
   - Grafana dashboard: `observability/grafana/leadline-dashboard.json`
- Runbooks:
   - `docs/runbooks.md`

## Phase 7 production readiness and launch

- Admin APIs:
   - `POST /v1/admin/provision`
   - `GET /v1/admin/tenants/{tenant_id}/plan-limits`
   - `POST /v1/admin/design-partners/{tenant_id}/enroll`
   - `POST /v1/admin/design-partners/{tenant_id}/promote`
- Plan limits enforced at runtime:
   - Leads, sessions, and messages creation limits by tenant plan
- Test layers:
   - Unit: `pytest -m unit`
   - Integration: `pytest -m integration`
   - Contract: `pytest -m contract`
   - End-to-end: `pytest -m e2e`
   - AI regression: `pytest -m ai_regression`
- Launch/operations docs:
   - `docs/onboarding-kit.md`
   - `docs/provisioning-workflow.md`
   - `docs/plan-limits.md`
   - `docs/staging-soak-test-plan.md`
   - `docs/rollback-plan.md`
   - `docs/oncall-readiness.md`
   - `docs/launch-rollout-plan.md`
   - `docs/design-partners-template.csv`
- Launch scripts:
   - `python scripts/staging_soak.py --token <admin_token>`
   - `python scripts/rollout_design_partners.py --token <admin_token>`
