# Phase 6 Outage Runbooks

## AI Degradation (OpenAI failures or latency)

1. Confirm current AI error/fallback rate in Grafana panel `AI Call Outcomes`.
2. Check alert `AIFallbackSpike` and inspect recent worker logs for `OpenAI analysis failed`.
3. Validate outbound network/DNS and OpenAI API status.
4. If external outage is confirmed:
   - keep worker running; heuristic fallback remains active
   - reduce queue ingest rate if backlog grows
   - notify stakeholders that intent quality is degraded
5. Recovery:
   - verify fallback rate returns to baseline
   - sample 20 recently scored leads for quality drift

## Messaging/Queue Degradation (SQS unavailable or publish skipped)

1. Confirm `Queue Publish Outcomes` panel and `QueuePublishFailures` alert.
2. Verify AWS/SQS credentials and endpoint reachability from API and worker.
3. If queue publish is skipped due to config drift:
   - restore queue URLs and restart API/worker
4. If queue receive/delete fails:
   - check AWS regional outage or IAM policy regression
   - drain dead-letter queues if enabled by infra
5. Recovery:
   - verify queue success rate and backlog drain
   - rerun missed lifecycle events for affected tenants

## Database Degradation (latency, connection failures)

1. Check `/readyz`, API 5xx, and latency dashboards.
2. Validate DB connection pool pressure and active locks.
3. If DB is partially degraded:
   - throttle high-volume write workflows
   - prioritize read-only and idempotent operations
4. If DB outage is confirmed:
   - move API to maintenance mode upstream
   - keep webhooks accepting only when idempotency store remains available
5. Recovery:
   - run integrity checks on lead/session/timeline/audit tables
   - replay queued events from safe checkpoints

## Security Incident Response (tenant isolation or auth anomaly)

1. Query `audit_logs` for suspicious cross-tenant patterns.
2. Confirm `X-Tenant-ID` mismatch rejections and 403 rates.
3. Rotate leaked secrets immediately (`JWT_SECRET`, integration tokens, `APP_DATA_ENCRYPTION_KEY`).
4. Revoke affected API keys and force user token refresh.
5. Run post-incident review and update alert thresholds.
