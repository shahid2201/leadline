# Provisioning Workflow

## API Endpoint

- `POST /v1/admin/provision`

### Request

```json
{
  "name": "Design Partner One",
  "slug": "design-partner-one",
  "owner_email": "owner@partner.test",
  "plan": "starter"
}
```

### Response

```json
{
  "tenant_id": "...",
  "user_id": "...",
  "api_key": "ll_live_...",
  "plan": "starter"
}
```

## Behavior

- Creates tenant, owner user, and default live API key
- Rejects duplicate tenant slug
- Sets launch metadata defaults in tenant settings

## Post-Provision Actions

1. Export OpenAPI docs for partner contract alignment.
2. Enroll as design partner (`/v1/admin/design-partners/{tenant_id}/enroll`).
3. Promote rollout percentage gradually (`/v1/admin/design-partners/{tenant_id}/promote`).
