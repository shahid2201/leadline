# Rollback Plan

## Trigger Conditions

- API error-rate breach for >15 minutes
- Queue processing backlog above critical threshold
- Tenant isolation incident or data corruption signal

## Steps

1. Freeze new design-partner promotions.
2. Shift traffic to previous stable deployment revision.
3. Pause integration fanout if downstream impact is detected.
4. Reconcile queued jobs and replay idempotent lifecycle events.
5. Run smoke checks for auth, lead CRUD, AI scoring, and webhooks.

## Validation Checklist

- `/healthz` and `/readyz` healthy
- Contract endpoints present
- No cross-tenant audit anomalies
- KPI and alert streams restored
