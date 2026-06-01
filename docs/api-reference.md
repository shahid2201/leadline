# LeadLine API Reference

This document describes the HTTP API implemented by the current FastAPI application, including authentication, tenant scoping, request and response models, and the operational side-effects triggered by each route.

Interactive docs are available at `/docs` when the app is running. The generated OpenAPI artifact committed to the repository is [docs/openapi.json](docs/openapi.json).

## Base conventions

- Base path: `/v1` for application routes.
- Unprefixed operational routes: `/healthz`, `/readyz`, `/metrics`.
- Content type: `application/json` unless noted otherwise.
- Multi-tenancy: all authenticated business routes are scoped to the tenant resolved from the bearer credential.
- Request tracing: every response includes `X-Request-ID`.
- Error shape: FastAPI default `{"detail": "..."}` for HTTP errors.

## Authentication and authorization

LeadLine protects all routes except health, metrics, docs, OpenAPI, and inbound webhook endpoints.

### Bearer authentication

Send credentials in the `Authorization` header:

```http
Authorization: Bearer <token>
```

The middleware supports two bearer token modes:

| Mode | How it is detected | Required data |
| --- | --- | --- |
| JWT | Token contains two `.` characters | `tenant_id`; optional `user_id`, `role`, `scopes` |
| API key | Any other bearer token | Matches stored API key prefix and hashed secret |

### JWT behavior

JWTs are validated with configured secret, algorithm, audience, issuer, and expiry. A valid token produces an auth context with:

- `auth_type`: `jwt`
- `tenant_id`
- `user_id`
- `role`
- `scopes`

### API key behavior

API keys are looked up by their first 16 characters and verified against the stored hash. A valid key produces an auth context with:

- `auth_type`: `api_key`
- `tenant_id`
- `api_key_id`
- `scopes`

Successful API key use updates `last_used_at`.

### Authorization rules

| Rule | Effect |
| --- | --- |
| Missing bearer token | `401 missing bearer token` |
| Empty bearer token | `401 empty bearer token` |
| Invalid JWT or API key | `401 invalid credentials` |
| `X-Tenant-ID` mismatch when enforcement is enabled | `403 tenant mismatch` |
| Rate limit exceeded | `429 rate limit exceeded` |
| Admin-only route accessed by non-admin/non-owner | `403 admin role required` |

### Auth-free routes

- `GET /healthz`
- `GET /readyz`
- `GET /metrics`
- `/docs`, `/redoc`, `/openapi.json`
- `POST /v1/webhooks/svix`
- `POST /v1/webhooks/hubspot`

## Cross-cutting behavior

### Tenant scoping

All business services read and write data using the `tenant_id` from the resolved auth context. The API never accepts a tenant identifier in request bodies for normal tenant-scoped operations.

### Logging, metrics, and audit

- Every HTTP request is logged with request ID, tenant, user, path, method, status code, and latency.
- Path logging can be PII-masked when masking is enabled.
- Prometheus counters and latency histograms are emitted for each request.
- When audit logging is enabled, non-health requests are persisted as audit log entries.

### Queue side-effects

Several synchronous API calls enqueue background work:

| Triggering route | Queue | Published event |
| --- | --- | --- |
| `POST /v1/sessions/{session_id}/messages` | `ai_jobs` | `message.created` |
| Lead lifecycle updates inside lead service | routing and integration worker queues | `lead.created`, `lead.updated`, `lead.score_updated` |
| `POST /v1/sequences/{sequence_id}/enroll` | `sequence_jobs` | `sequence.step.execute` |
| `POST /v1/admin/dlq/{job_id}/replay` | queue from failed job | original failed payload |

If SQS queue URLs are not configured, publishing becomes a safe no-op.

## Operational endpoints

### `GET /healthz`

Liveness probe.

Response:

```json
{"status": "ok"}
```

### `GET /readyz`

Database readiness probe.

Success response:

```json
{"status": "ready"}
```

Failure response: `503 database unavailable`

### `GET /metrics`

Returns Prometheus metrics in text format.

## Auth introspection

### `GET /v1/auth/me`

Returns the current request auth context.

Response fields:

| Field | Type | Notes |
| --- | --- | --- |
| `auth_type` | string | `jwt` or `api_key` |
| `tenant_id` | string | Always present for authenticated requests |
| `user_id` | string or null | Present for JWT-based user auth |
| `api_key_id` | string or null | Present for API-key auth |
| `scopes` | array of string or null | Scope list from the auth context |
| `role` | string or null | Used by admin-only routes |

## Leads API

Base path: `/v1/leads`

### Lead object

Returned lead records include:

- Identity: `id`, `tenant_id`
- Contact fields: `name`, `email`, `phone`, `company`, `role`
- Attribution fields: `channel`, `campaign`, `utm_source`, `utm_medium`, `utm_campaign`
- Qualification fields: `status`, `stage`, `lead_score`, `fit_score`, `engagement_score`
- Routing fields: `owner_user_id`, `assigned_team_id`, `assigned_queue_name`
- Consent and extensibility: `marketing_opt_in`, `allowed_channels`, `custom_fields`
- Timestamps: `created_at`, `updated_at`

### `POST /v1/leads`

Creates a lead for the authenticated tenant.

Request body:

```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "phone": "+1-555-0100",
  "company": "Analytical Engines",
  "role": "CTO",
  "channel": "chat",
  "campaign": "launch-2026",
  "utm_source": "google",
  "utm_medium": "cpc",
  "utm_campaign": "brand",
  "status": "new",
  "stage": "captured",
  "lead_score": 0,
  "fit_score": 0,
  "engagement_score": 0,
  "owner_user_id": null,
  "assigned_team_id": null,
  "assigned_queue_name": null,
  "marketing_opt_in": false,
  "allowed_channels": ["email", "sms"],
  "custom_fields": {"product": "enterprise"}
}
```

Response:

```json
{
  "deduplicated": false,
  "lead": {
    "id": "lead_123",
    "tenant_id": "tenant_123",
    "name": "Ada Lovelace"
  }
}
```

Behavior:

- Deduplicates by normalized email or phone within the tenant.
- Creates a lead timeline entry when a new lead is created.
- Enforces tenant plan limits for lead creation.
- Publishes lead lifecycle events for downstream routing, sequence, and integration processing.

### `GET /v1/leads`

Lists tenant leads.

Query parameters:

| Name | Type | Notes |
| --- | --- | --- |
| `status` | string | Optional status filter |

Response: array of lead objects.

### `GET /v1/leads/{lead_id}`

Returns a single lead.

Failure: `404 lead not found`

### `PATCH /v1/leads/{lead_id}`

Updates any subset of lead fields.

Behavior:

- Returns the updated lead.
- Publishes `lead.updated` when the lead exists.

Failure: `404 lead not found`

### `DELETE /v1/leads/{lead_id}`

Deletes the lead and returns `204 No Content`.

Failure: `404 lead not found`

### `POST /v1/leads/{lead_id}/timeline`

Creates a timeline event for a lead.

Request body:

```json
{
  "type": "note_added",
  "payload": {"note": "Requested pricing follow-up"}
}
```

Response fields:

- `id`
- `tenant_id`
- `lead_id`
- `type`
- `payload`
- `created_at`
- `updated_at`

Failure: `404 lead not found`

### `GET /v1/leads/{lead_id}/timeline`

Lists all timeline events for a lead.

### `POST /v1/leads/{lead_id}/attach-session`

Associates an existing session with a lead.

Request body:

```json
{
  "session_id": "session_123"
}
```

Response:

```json
{
  "session_id": "session_123",
  "lead_id": "lead_123"
}
```

Failure: `404 lead or session not found`

## Timeline API

Base path: `/v1/timeline`

### `GET /v1/timeline/{event_id}`

Returns a single timeline event.

Failure: `404 timeline event not found`

### `PATCH /v1/timeline/{event_id}`

Updates `type` and/or `payload`.

Failure: `404 timeline event not found`

### `DELETE /v1/timeline/{event_id}`

Deletes a timeline event and returns `204 No Content`.

Failure: `404 timeline event not found`

## Sessions and messages API

Base path: `/v1/sessions`

### Session object

Fields:

- `id`, `tenant_id`, `visitor_id`, `lead_id`
- `started_at`, `ended_at`
- `metadata` from the stored `session_metadata` field
- `created_at`, `updated_at`

### Message object

Fields:

- `id`, `tenant_id`, `session_id`
- `sender_type`, `content`
- AI annotations: `intent`, `entities`, `sentiment`, `urgency`, `topics`
- `created_at`, `updated_at`

### `POST /v1/sessions`

Creates a session.

Request body:

```json
{
  "visitor_id": "visitor_123",
  "lead_id": null,
  "started_at": null,
  "ended_at": null,
  "metadata": {
    "url": "/pricing",
    "utm_campaign": "launch"
  }
}
```

Behavior:

- Enforces tenant session plan limits.
- Returns the created session object.

### `GET /v1/sessions`

Lists sessions for the tenant.

### `GET /v1/sessions/{session_id}`

Returns one session.

Failure: `404 session not found`

### `PATCH /v1/sessions/{session_id}`

Updates `lead_id`, `ended_at`, and/or `metadata`.

Failure: `404 session not found`

### `DELETE /v1/sessions/{session_id}`

Deletes the session and returns `204 No Content`.

Failure: `404 session not found`

### `POST /v1/sessions/{session_id}/messages`

Creates a message in a session.

Request body:

```json
{
  "sender_type": "visitor",
  "content": "We need pricing for 50 seats",
  "intent": null,
  "entities": {},
  "sentiment": null,
  "urgency": null,
  "topics": []
}
```

Behavior:

- Enforces tenant message plan limits.
- Creates the message synchronously.
- Publishes `message.created` to the AI queue for later enrichment.

Failure: `404 session not found`

### `GET /v1/sessions/{session_id}/messages`

Lists messages for the session.

## Messages API

Base path: `/v1/messages`

### `GET /v1/messages/{message_id}`

Returns a single message.

Failure: `404 message not found`

### `PATCH /v1/messages/{message_id}`

Updates any subset of message fields, including AI-derived annotations.

Failure: `404 message not found`

### `DELETE /v1/messages/{message_id}`

Deletes a message and returns `204 No Content`.

Failure: `404 message not found`

## Routing rules API

Base path: `/v1/routing/rules`

Authorization: admin or owner role required.

### Routing rule object

Fields:

- `id`, `tenant_id`, `name`
- `priority`
- `enabled`
- `conditions`: list of condition dictionaries
- `action`
- `action_payload`
- `created_at`, `updated_at`

### `POST /v1/routing/rules`

Creates a routing rule.

Request body:

```json
{
  "name": "High score to enterprise team",
  "priority": 100,
  "enabled": true,
  "conditions": [
    {"field": "lead_score", "operator": "gte", "value": 80}
  ],
  "action": "assign_team",
  "action_payload": {"assigned_team_id": "team_enterprise"}
}
```

Supported actions in the implementation:

- `assign_user`
- `assign_team`
- `queue`

### `GET /v1/routing/rules`

Lists all routing rules for the tenant.

### `GET /v1/routing/rules/{rule_id}`

Returns one rule.

Failure: `404 routing rule not found`

### `PATCH /v1/routing/rules/{rule_id}`

Updates any subset of rule fields.

Failure: `404 routing rule not found`

### `DELETE /v1/routing/rules/{rule_id}`

Deletes the rule and returns `204 No Content`.

Failure: `404 routing rule not found`

## Sequences API

Base path: `/v1/sequences`

Authorization: admin or owner role required.

### Sequence object

Fields:

- `id`, `tenant_id`, `name`, `description`, `trigger`, `status`, `created_at`, `updated_at`

### Sequence step object

Fields:

- `id`, `sequence_id`, `order_index`, `type`, `delay_seconds`, `template`, `created_at`, `updated_at`

### Enrollment object

Fields:

- `id`, `tenant_id`, `lead_id`, `sequence_id`, `status`, `current_step_index`, `created_at`, `updated_at`

### `POST /v1/sequences`

Creates a sequence.

Request body:

```json
{
  "name": "High intent follow-up",
  "description": "Three touch sequence for inbound demo requests",
  "trigger": "lead.created",
  "status": "draft"
}
```

### `GET /v1/sequences`

Lists sequences for the tenant.

### `GET /v1/sequences/{sequence_id}`

Returns one sequence.

Failure: `404 sequence not found`

### `PATCH /v1/sequences/{sequence_id}`

Updates any subset of sequence fields.

Failure: `404 sequence not found`

### `DELETE /v1/sequences/{sequence_id}`

Deletes the sequence and returns `204 No Content`.

Failure: `404 sequence not found`

### `POST /v1/sequences/{sequence_id}/steps`

Creates a step for the sequence.

Request body:

```json
{
  "order_index": 1,
  "type": "email",
  "delay_seconds": 0,
  "template": "thanks-for-your-interest"
}
```

Supported step types in the worker pipeline:

- `email`
- `sms`
- `wait`
- `task`

Failure: `404 sequence not found`

### `GET /v1/sequences/{sequence_id}/steps`

Lists steps for the sequence.

### `PATCH /v1/sequences/{sequence_id}/steps/{step_id}`

Updates any subset of step fields.

Failure: `404 step not found`

### `DELETE /v1/sequences/{sequence_id}/steps/{step_id}`

Deletes the step and returns `204 No Content`.

Failure: `404 step not found`

### `POST /v1/sequences/{sequence_id}/enroll`

Enrolls a lead into the sequence.

Request body:

```json
{
  "lead_id": "lead_123"
}
```

Behavior:

- Creates a sequence enrollment record.
- Publishes `sequence.step.execute` to the sequence queue.

Failure: `404 lead or sequence not found`

## Integrations API

Base path: `/v1/integrations`

Authorization: admin or owner role required.

### `POST /v1/integrations/hubspot/leads/{lead_id}/sync`

Fetches the tenant lead and synchronizes it to HubSpot.

Response:

```json
{"synced": true}
```

Failure: `404 lead not found`

Behavior:

- Persists integration connection metadata.
- Commits the database transaction after sync attempt.

### `GET /v1/integrations/calendar/availability`

Returns available time slots.

Query parameters:

| Name | Type | Required |
| --- | --- | --- |
| `calendar_id` | string | yes |
| `time_min` | RFC 3339 datetime | yes |
| `time_max` | RFC 3339 datetime | yes |

Response item:

```json
{
  "start": "2026-06-01T09:00:00Z",
  "end": "2026-06-01T09:30:00Z"
}
```

### `POST /v1/integrations/calendar/bookings`

Creates a calendar booking.

Request body:

```json
{
  "calendar_id": "primary",
  "summary": "LeadLine demo",
  "start": "2026-06-01T09:00:00Z",
  "end": "2026-06-01T09:30:00Z"
}
```

Response:

```json
{"booked": true}
```

## Webhooks API

Base path: `/v1/webhooks`

These routes bypass bearer authentication and instead enforce provider-specific signature validation.

### `POST /v1/webhooks/svix`

Required headers:

- `svix-id`
- `svix-timestamp`
- `svix-signature`

Behavior:

- Reads the raw request body.
- Validates the Svix signature through the webhook service.
- Uses `tenant_id` and `type` from the JSON payload when present.
- Persists an idempotency record for the provider event.
- Returns the existing status if the event was already seen.
- Marks the event `processed` on success or `failed` on exception.

Possible responses:

- `400 missing svix headers`
- `200 {"status": "processed"}`
- `200 {"status": "received"}` or other stored status for duplicate delivery
- `500 failed`

### `POST /v1/webhooks/hubspot`

Required header:

- `x-hubspot-signature`

Behavior:

- Requires `HUBSPOT_WEBHOOK_SECRET` configuration.
- Verifies an HMAC SHA-256 signature over the raw payload bytes.
- Accepts either a single object or a list of event objects.
- Uses `tenantId`, `eventId` or `id`, and `subscriptionType` from each item.
- Stores idempotency records and marks new events as processed.

Possible responses:

- `500 HUBSPOT_WEBHOOK_SECRET is not configured`
- `400 missing hubspot signature`
- `401 invalid signature`
- `200 {"status": "processed"}`

## Admin API

Base path: `/v1/admin`

Authorization: admin or owner role required.

### `POST /v1/admin/provision`

Creates a tenant, owner user, and API key.

Request body:

```json
{
  "name": "Acme Inc",
  "slug": "acme",
  "owner_email": "owner@acme.test",
  "plan": "starter"
}
```

Response:

```json
{
  "tenant_id": "tenant_123",
  "user_id": "user_123",
  "api_key": "ll_live_...",
  "plan": "starter"
}
```

Failure: `400` for invalid or conflicting tenant provisioning input.

### `GET /v1/admin/tenants/{tenant_id}/plan-limits`

Returns the tenant's current plan and resolved plan limits.

Response:

```json
{
  "plan": "starter",
  "limits": {
    "max_leads": 1000,
    "max_sessions": 5000,
    "max_messages": 50000
  }
}
```

Failure: `404 tenant not found`

### `POST /v1/admin/design-partners/{tenant_id}/enroll`

Enrolls a tenant into a design-partner cohort.

Request body:

```json
{
  "cohort": "wave-1",
  "launch_notes": "Priority onboarding"
}
```

Response:

```json
{
  "tenant_id": "tenant_123",
  "enrolled": true,
  "cohort": "wave-1"
}
```

Failure: `404` when provisioning service cannot find the tenant.

### `POST /v1/admin/design-partners/{tenant_id}/promote`

Promotes rollout percentage for a tenant.

Request body:

```json
{
  "rollout_percentage": 50
}
```

Response:

```json
{
  "tenant_id": "tenant_123",
  "rollout_percentage": 50
}
```

### `GET /v1/admin/tenants/{tenant_id}/usage`

Returns usage summaries over a date window.

Query parameters:

| Name | Type | Default | Range |
| --- | --- | --- | --- |
| `days` | integer | `30` | `1..365` |

Usage record fields:

- `record_date`
- `ai_tokens_used`
- `messages_sent`
- `emails_sent`
- `sms_sent`
- `leads_created`
- `sessions_created`

Failure: `404 tenant not found`

### `GET /v1/admin/dlq`

Lists pending dead-lettered jobs.

Query parameters:

| Name | Type | Notes |
| --- | --- | --- |
| `queue_name` | string | Optional queue filter |

Response shape:

```json
{
  "total": 1,
  "jobs": [
    {
      "id": "job_123",
      "queue_name": "sequence_jobs",
      "event_type": "sequence.step.execute",
      "error": "provider timeout",
      "attempts": 3,
      "status": "pending",
      "tenant_id": "tenant_123",
      "created_at": "2026-06-01T00:00:00+00:00"
    }
  ]
}
```

### `POST /v1/admin/dlq/{job_id}/replay`

Republishes the failed job payload to its original queue and marks it replayed.

Response:

```json
{
  "job_id": "job_123",
  "replayed": true
}
```

Failure: `404 job not found`

## Background systems connected to the API

These are not directly exposed as HTTP routes, but they shape API behavior and expectations.

### AI pipeline

- Triggered by `message.created` queue events.
- Enriches messages with `intent`, `entities`, `sentiment`, `urgency`, and `topics`.
- Computes lead scoring fields when a message is attached to a lead.
- Uses OpenAI when configured, with deterministic fallback logic.
- Caches idempotent AI results in Redis.

### Routing engine

- Triggered by lead lifecycle events.
- Evaluates enabled rules in deterministic order.
- Applies assignment changes to lead ownership, team assignment, or queue assignment.

### Sequence execution

- Triggered by enrollment and lifecycle events.
- Processes `email`, `sms`, `wait`, and `task` step types.
- Records timeline events for sequence execution.

### Integrations and delivery

- Email delivery uses Amazon SES when configured.
- SMS delivery uses Twilio when configured.
- CRM and calendar flows persist integration connection metadata.

## Documentation artifacts in the repository

Related files:

- [README.md](README.md)
- [docs/openapi.json](docs/openapi.json)
- [docs/plan-limits.md](docs/plan-limits.md)
- [docs/provisioning-workflow.md](docs/provisioning-workflow.md)
- [docs/runbooks.md](docs/runbooks.md)

For client generation or contract assertions, prefer the OpenAPI artifact. For operator-facing context and endpoint behavior, use this reference.# LeadLine API Reference

This document describes the HTTP API implemented by the current LeadLine application. It is based on the routers mounted in `app/main.py`, the request and response schemas in `app/schemas/`, and the auth, worker, observability, and webhook behavior wired into the app.

## API overview

- Base path: `/v1` for application APIs.
- Unprefixed operational endpoints: `/healthz`, `/readyz`, `/metrics`.
- Interactive docs at runtime: `/docs`.
- OpenAPI artifact exported by the repo: `docs/openapi.json`.
- Every request response includes `X-Request-ID`.

## Authentication and authorization

All non-excluded application routes require:

```http
Authorization: Bearer <token>
```

LeadLine supports two bearer token modes.

### JWT mode

If the token looks like a JWT (`x.y.z`), the middleware validates it using configured issuer, audience, algorithm, and secret settings.

Expected claims:

- `tenant_id` required
- `user_id` optional
- `role` optional
- `scopes` optional list

### API key mode

If the bearer token is not a JWT, it is treated as an API key. The app looks up keys by prefix and verifies the stored hash before building tenant context.

### Tenant isolation

- All service access is tenant-scoped through `AuthContext`.
- If `X-Tenant-ID` is sent and tenant-header matching is enabled, it must match the authenticated tenant.

### Role checks

- Standard authenticated routes depend on tenant context only.
- Admin routes depend on `require_admin`, which allows only `admin` and `owner` roles.

### Rate limiting

- Applied after authentication.
- Enforced per tenant.
- Exceeded limit returns `429 rate limit exceeded`.

### Unauthenticated routes

These paths bypass auth middleware:

- `/healthz`
- `/readyz`
- `/metrics`
- `/docs`
- `/openapi.json`
- `/redoc`
- `/v1/webhooks/svix`
- `/v1/webhooks/hubspot`

Webhook routes still enforce provider signature validation.

## API conventions

### Common response behavior

- Successful read/write responses return JSON bodies matching Pydantic schemas.
- Delete operations return `204 No Content`.
- Missing records generally return `404` with a simple `detail` string.
- Auth failures return `401`.
- Role or tenant mismatches return `403`.
- Rate limit violations return `429`.

### Auditing, logging, and metrics

- Request logs include request id, tenant id, user id, path, method, status code, and latency.
- `/healthz`, `/readyz`, and `/metrics` are excluded from audit persistence.
- Prometheus counters and latency metrics are emitted for HTTP requests.
- When enabled, audit entries are persisted for API calls.

## Operational endpoints

### `GET /healthz`

Liveness probe.

Response:

```json
{
  "status": "ok"
}
```

### `GET /readyz`

Database readiness probe.

Success response:

```json
{
  "status": "ready"
}
```

Failure response:

- `503` with `database unavailable`

### `GET /metrics`

Returns Prometheus metrics output.

## Auth inspection

### `GET /v1/auth/me`

Returns the current resolved auth context.

Response shape:

```json
{
  "auth_type": "jwt",
  "tenant_id": "tenant_123",
  "user_id": "user_123",
  "api_key_id": null,
  "scopes": ["*"],
  "role": "admin"
}
```

## Leads API

Base path: `/v1/leads`

### Lead object

Lead responses include:

- `id`, `tenant_id`
- identity and attribution fields: `name`, `email`, `phone`, `company`, `role`, `channel`, `campaign`, `utm_source`, `utm_medium`, `utm_campaign`
- lifecycle fields: `status`, `stage`
- scoring fields: `lead_score`, `fit_score`, `engagement_score`
- routing fields: `owner_user_id`, `assigned_team_id`, `assigned_queue_name`
- consent and extensibility fields: `marketing_opt_in`, `allowed_channels`, `custom_fields`
- timestamps: `created_at`, `updated_at`

### `POST /v1/leads`

Creates a lead for the authenticated tenant.

Request body:

```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+1-555-0101",
  "company": "Acme",
  "role": "Head of RevOps",
  "channel": "chat",
  "campaign": "summer-launch",
  "utm_source": "google",
  "utm_medium": "cpc",
  "utm_campaign": "brand",
  "status": "new",
  "stage": "captured",
  "lead_score": 0,
  "fit_score": 0,
  "engagement_score": 0,
  "owner_user_id": null,
  "assigned_team_id": null,
  "assigned_queue_name": null,
  "marketing_opt_in": false,
  "allowed_channels": ["email", "sms"],
  "custom_fields": {}
}
```

Response:

```json
{
  "deduplicated": false,
  "lead": {
    "id": "lead_123",
    "tenant_id": "tenant_123",
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "+1-555-0101",
    "company": "Acme",
    "role": "Head of RevOps",
    "channel": "chat",
    "campaign": "summer-launch",
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "brand",
    "status": "new",
    "stage": "captured",
    "lead_score": 0,
    "fit_score": 0,
    "engagement_score": 0,
    "owner_user_id": null,
    "assigned_team_id": null,
    "assigned_queue_name": null,
    "marketing_opt_in": false,
    "allowed_channels": ["email", "sms"],
    "custom_fields": {},
    "created_at": "2026-06-01T12:00:00Z",
    "updated_at": "2026-06-01T12:00:00Z"
  }
}
```

Behavior notes:

- Deduplicates by tenant using email or phone where applicable.
- Enforces tenant plan limits for lead creation.
- Creates lifecycle timeline data in the service layer.
- Publishes lifecycle events used by routing, sequences, and integrations.

### `GET /v1/leads`

Lists tenant leads.

Query parameters:

- `status` optional filter

Returns `LeadResponse[]`.

### `GET /v1/leads/{lead_id}`

Returns a single lead.

Failure:

- `404 lead not found`

### `PATCH /v1/leads/{lead_id}`

Partially updates any writable lead field.

Request body uses the same lead fields as create, all optional.

Failure:

- `404 lead not found`

Behavior notes:

- Publishes lead update lifecycle events.

### `DELETE /v1/leads/{lead_id}`

Deletes a lead.

Failure:

- `404 lead not found`

### `POST /v1/leads/{lead_id}/timeline`

Creates a timeline event for a lead.

Request body:

```json
{
  "type": "note_added",
  "payload": {
    "body": "Requested pricing follow-up"
  }
}
```

Response fields:

- `id`, `tenant_id`, `lead_id`, `type`, `payload`, `created_at`, `updated_at`

Failure:

- `404 lead not found`

### `GET /v1/leads/{lead_id}/timeline`

Lists timeline events for a lead.

Returns `TimelineEventResponse[]`.

### `POST /v1/leads/{lead_id}/attach-session`

Attaches an existing session to a lead.

Request body:

```json
{
  "session_id": "session_123"
}
```

Response:

```json
{
  "session_id": "session_123",
  "lead_id": "lead_123"
}
```

Failure:

- `404 lead or session not found`

## Timeline API

Base path: `/v1/timeline`

### `GET /v1/timeline/{event_id}`

Returns a single timeline event.

Failure:

- `404 timeline event not found`

### `PATCH /v1/timeline/{event_id}`

Partially updates timeline event fields.

Request body:

```json
{
  "type": "status_changed",
  "payload": {
    "from": "new",
    "to": "qualified"
  }
}
```

Failure:

- `404 timeline event not found`

### `DELETE /v1/timeline/{event_id}`

Deletes a timeline event.

Failure:

- `404 timeline event not found`

## Sessions and messages API

Base path: `/v1/sessions`

### Session object

Fields:

- `id`, `tenant_id`, `visitor_id`, `lead_id`
- `started_at`, `ended_at`
- `metadata` mapped from the model attribute `session_metadata`
- `created_at`, `updated_at`

### `POST /v1/sessions`

Creates an anonymous or lead-linked conversation session.

Request body:

```json
{
  "visitor_id": "visitor_123",
  "lead_id": null,
  "started_at": "2026-06-01T12:00:00Z",
  "ended_at": null,
  "metadata": {
    "url": "/pricing",
    "referrer": "https://google.com",
    "utm_source": "google"
  }
}
```

Behavior notes:

- Enforces tenant plan limits for session creation.

### `GET /v1/sessions`

Lists tenant sessions.

### `GET /v1/sessions/{session_id}`

Returns one session.

Failure:

- `404 session not found`

### `PATCH /v1/sessions/{session_id}`

Updates `lead_id`, `ended_at`, or session metadata.

Failure:

- `404 session not found`

### `DELETE /v1/sessions/{session_id}`

Deletes a session.

Failure:

- `404 session not found`

### `POST /v1/sessions/{session_id}/messages`

Creates a message inside a session.

Request body:

```json
{
  "sender_type": "visitor",
  "content": "We need pricing for 200 seats.",
  "intent": null,
  "entities": {},
  "sentiment": null,
  "urgency": null,
  "topics": []
}
```

Response fields:

- `id`, `tenant_id`, `session_id`, `sender_type`, `content`
- `intent`, `entities`, `sentiment`, `urgency`, `topics`
- `created_at`, `updated_at`

Behavior notes:

- Enforces tenant plan limits for message creation.
- Publishes an `ai_jobs` queue event with `event=message.created`.
- AI workers can later enrich the stored message with intent, entities, sentiment, urgency, and topics.

Failure:

- `404 session not found`

### `GET /v1/sessions/{session_id}/messages`

Lists messages for a session.

## Messages API

Base path: `/v1/messages`

### `GET /v1/messages/{message_id}`

Returns a single message.

Failure:

- `404 message not found`

### `PATCH /v1/messages/{message_id}`

Partially updates message fields.

Failure:

- `404 message not found`

### `DELETE /v1/messages/{message_id}`

Deletes a message.

Failure:

- `404 message not found`

## Routing rules API

Base path: `/v1/routing/rules`

Authorization:

- Admin-only

### Routing rule object

Fields:

- `id`, `tenant_id`, `name`
- `priority`, `enabled`
- `conditions` list of rule predicates
- `action`
- `action_payload`
- `created_at`, `updated_at`

### `POST /v1/routing/rules`

Creates a routing rule.

Request body:

```json
{
  "name": "High-score EMEA enterprise",
  "priority": 10,
  "enabled": true,
  "conditions": [
    {"field": "lead_score", "operator": "gte", "value": 80},
    {"field": "region", "operator": "eq", "value": "emea"}
  ],
  "action": "assign_team",
  "action_payload": {
    "assigned_team_id": "team_enterprise_emea"
  }
}
```

### `GET /v1/routing/rules`

Lists all routing rules for the tenant.

### `GET /v1/routing/rules/{rule_id}`

Returns one rule.

Failure:

- `404 routing rule not found`

### `PATCH /v1/routing/rules/{rule_id}`

Partially updates the rule.

Failure:

- `404 routing rule not found`

### `DELETE /v1/routing/rules/{rule_id}`

Deletes a rule.

Failure:

- `404 routing rule not found`

Behavior notes:

- Rules are consumed by routing services and worker pipelines on lead lifecycle events.
- Action payloads support assignment outcomes such as user, team, or queue assignment.

## Sequences API

Base path: `/v1/sequences`

Authorization:

- Admin-only

### Sequence object

Fields:

- `id`, `tenant_id`, `name`, `description`, `trigger`, `status`, `created_at`, `updated_at`

### Sequence step object

Fields:

- `id`, `sequence_id`, `order_index`, `type`, `delay_seconds`, `template`, `created_at`, `updated_at`

### Enrollment object

Fields:

- `id`, `tenant_id`, `lead_id`, `sequence_id`, `status`, `current_step_index`, `created_at`, `updated_at`

### `POST /v1/sequences`

Creates a sequence.

Request body:

```json
{
  "name": "High intent follow-up",
  "description": "Immediate outreach for qualified leads",
  "trigger": "lead.created",
  "status": "draft"
}
```

### `GET /v1/sequences`

Lists sequences.

### `GET /v1/sequences/{sequence_id}`

Returns one sequence.

Failure:

- `404 sequence not found`

### `PATCH /v1/sequences/{sequence_id}`

Partially updates a sequence.

Failure:

- `404 sequence not found`

### `DELETE /v1/sequences/{sequence_id}`

Deletes a sequence.

Failure:

- `404 sequence not found`

### `POST /v1/sequences/{sequence_id}/steps`

Creates a sequence step.

Request body:

```json
{
  "order_index": 1,
  "type": "email",
  "delay_seconds": 0,
  "template": "intro_followup_v1"
}
```

Failure:

- `404 sequence not found`

### `GET /v1/sequences/{sequence_id}/steps`

Lists steps for a sequence.

### `PATCH /v1/sequences/{sequence_id}/steps/{step_id}`

Partially updates a step.

Failure:

- `404 step not found`

### `DELETE /v1/sequences/{sequence_id}/steps/{step_id}`

Deletes a step.

Failure:

- `404 step not found`

### `POST /v1/sequences/{sequence_id}/enroll`

Enrolls a lead into a sequence.

Request body:

```json
{
  "lead_id": "lead_123"
}
```

Behavior notes:

- Publishes a `sequence_jobs` event with `event=sequence.step.execute`.
- Worker execution then handles step processing and timeline updates.

Failure:

- `404 lead or sequence not found`

## Integrations API

Base path: `/v1/integrations`

Authorization:

- Admin-only

### `POST /v1/integrations/hubspot/leads/{lead_id}/sync`

Loads the lead from the tenant-scoped lead service and submits a CRM sync request.

Response:

```json
{
  "synced": true
}
```

Failure:

- `404 lead not found`

Behavior notes:

- Commits integration state after sync attempts.
- Uses the integration repository to persist connection/sync metadata.

### `GET /v1/integrations/calendar/availability`

Query parameters:

- `calendar_id` required
- `time_min` required datetime
- `time_max` required datetime

Response:

```json
[
  {
    "start": "2026-06-01T15:00:00Z",
    "end": "2026-06-01T15:30:00Z"
  }
]
```

### `POST /v1/integrations/calendar/bookings`

Request body:

```json
{
  "calendar_id": "primary",
  "summary": "LeadLine demo",
  "start": "2026-06-01T15:00:00Z",
  "end": "2026-06-01T15:30:00Z"
}
```

Response:

```json
{
  "booked": true
}
```

## Webhooks API

Base path: `/v1/webhooks`

These endpoints bypass bearer auth but validate provider signatures.

### `POST /v1/webhooks/svix`

Required headers:

- `svix-id`
- `svix-timestamp`
- `svix-signature`

Behavior:

- Reads raw request body and parsed JSON.
- Verifies Svix signature through the webhook service.
- Uses idempotency storage keyed by tenant, provider, and source event id.
- Returns existing status if the event was already seen.
- Marks events as processed or failed.

Success response:

```json
{
  "status": "processed"
}
```

Common failures:

- `400 missing svix headers`
- `500 failed`

### `POST /v1/webhooks/hubspot`

Required header:

- `x-hubspot-signature`

Behavior:

- Requires configured `HUBSPOT_WEBHOOK_SECRET`.
- Validates HMAC SHA-256 signature against the raw payload.
- Accepts either a single event or a list of events.
- Stores idempotent webhook processing state per incoming event.

Success response:

```json
{
  "status": "processed"
}
```

Common failures:

- `500 HUBSPOT_WEBHOOK_SECRET is not configured`
- `400 missing hubspot signature`
- `401 invalid signature`

## Admin API

Base path: `/v1/admin`

Authorization:

- Admin-only

### `POST /v1/admin/provision`

Provisions a tenant, owner user, and API key.

Request body:

```json
{
  "name": "Acme",
  "slug": "acme",
  "owner_email": "owner@acme.com",
  "plan": "starter"
}
```

Response:

```json
{
  "tenant_id": "tenant_123",
  "user_id": "user_123",
  "api_key": "ll_live_xxx",
  "plan": "starter"
}
```

Failure:

- `400` on validation or provisioning conflicts surfaced as `ValueError`

### `GET /v1/admin/tenants/{tenant_id}/plan-limits`

Returns plan and computed limits for the tenant.

Response:

```json
{
  "plan": "starter",
  "limits": {
    "max_leads": 1000,
    "max_sessions": 5000,
    "max_messages": 20000
  }
}
```

Failure:

- `404 tenant not found`

### `POST /v1/admin/design-partners/{tenant_id}/enroll`

Enrolls a tenant in a design-partner cohort.

Request body:

```json
{
  "cohort": "wave-1",
  "launch_notes": "Priority onboarding"
}
```

Response:

```json
{
  "tenant_id": "tenant_123",
  "enrolled": true,
  "cohort": "wave-1"
}
```

### `POST /v1/admin/design-partners/{tenant_id}/promote`

Updates rollout percentage for a tenant.

Request body:

```json
{
  "rollout_percentage": 50
}
```

Response:

```json
{
  "tenant_id": "tenant_123",
  "rollout_percentage": 50
}
```

### `GET /v1/admin/tenants/{tenant_id}/usage`

Query parameters:

- `days` optional, default `30`, range `1..365`

Response:

```json
{
  "tenant_id": "tenant_123",
  "days": 30,
  "records": [
    {
      "record_date": "2026-06-01",
      "ai_tokens_used": 1200,
      "messages_sent": 40,
      "emails_sent": 10,
      "sms_sent": 2,
      "leads_created": 8,
      "sessions_created": 12
    }
  ]
}
```

Failure:

- `404 tenant not found`

### `GET /v1/admin/dlq`

Lists pending dead-letter jobs.

Query parameters:

- `queue_name` optional filter

Response:

```json
{
  "total": 1,
  "jobs": [
    {
      "id": "job_123",
      "queue_name": "sequence_jobs",
      "event_type": "sequence.step.execute",
      "error": "provider unavailable",
      "attempts": 3,
      "status": "pending",
      "tenant_id": "tenant_123",
      "created_at": "2026-06-01T12:00:00Z"
    }
  ]
}
```

### `POST /v1/admin/dlq/{job_id}/replay`

Republishes a failed job to its original queue and marks it as replayed.

Response:

```json
{
  "job_id": "job_123",
  "replayed": true
}
```

Failure:

- `404 job not found`

## Background side effects and asynchronous flows

These are important when integrating with the API because several write endpoints do more than return a record.

### Message ingestion

- `POST /v1/sessions/{session_id}/messages` publishes `message.created` to `ai_jobs`.
- The AI pipeline can annotate messages with intent, entities, sentiment, urgency, and topics.
- If the message is associated with a lead, downstream scoring can update the lead.

### Lead lifecycle

- Lead create and update flows publish lifecycle events used by routing, sequences, and integration handlers.
- Routing can update `owner_user_id`, `assigned_team_id`, or `assigned_queue_name`.

### Sequence execution

- Sequence enrollment publishes `sequence.step.execute` to `sequence_jobs`.
- Worker execution can emit delivery activity and lead timeline events.

### Webhooks

- Inbound webhook events are idempotent and persisted.
- Duplicate webhooks return current processing state rather than reprocessing.

## Observability and security notes

- `/metrics` exposes Prometheus-compatible metrics.
- Request tracing is configured at app startup.
- Request paths may be PII-masked in logs depending on configuration.
- Audit logging is enabled for most API routes when configured.
- Admin APIs rely on role enforcement, not only scopes.

## Suggested consumer workflow

1. Authenticate with a JWT or API key bearer token.
2. Create sessions and messages for visitor activity.
3. Create or deduplicate leads as identity becomes known.
4. Use timeline events to persist important sales or automation context.
5. Manage routing rules and sequences through admin endpoints.
6. Use integrations and webhook endpoints to connect external systems.
7. Use admin usage and DLQ endpoints for operational control.

## Source of truth

This document is a human-readable reference. The generated machine-readable contract for the current app is `docs/openapi.json`, and the live runtime schema is available from `/openapi.json` when the app is running.