# Plan Limits

## Default Profiles

- `starter`: `max_leads=500`, `max_sessions=3000`, `max_messages=20000`
- `growth`: `max_leads=5000`, `max_sessions=30000`, `max_messages=250000`
- `enterprise`: high-cap capacity defaults

## Enforcement Points

- Lead creation (`POST /v1/leads`)
- Session creation (`POST /v1/sessions`)
- Message creation (`POST /v1/sessions/{id}/messages`)

## Limit Overrides

Tenant-level overrides may be defined in `tenant.settings.plan_limits`:

```json
{
  "plan_limits": {
    "max_leads": 1000,
    "max_sessions": 5000,
    "max_messages": 50000
  }
}
```

## Inspection Endpoint

- `GET /v1/admin/tenants/{tenant_id}/plan-limits`
