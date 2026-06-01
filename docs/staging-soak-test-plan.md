# Staging Soak Test Plan

## Goal

Validate 24-72h stability for lifecycle, queueing, AI fallback, and integrations before production promotion.

## Test Cadence

1. Warmup: 30 minutes
2. Baseline soak: 24 hours
3. Spike windows: 3x daily for 20 minutes
4. Recovery verification after each spike

## Mandatory Checks

- API p95 latency and 5xx rates
- Queue publish/consume continuity
- AI fallback ratio
- Webhook idempotency consistency
- Audit log write throughput

## Exit Criteria

- No sustained P1 alerts
- No data integrity drift in lead/session/timeline chains
- Rollback rehearsal completed in staging
