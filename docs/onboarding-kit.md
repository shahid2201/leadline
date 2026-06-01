# Onboarding Kit

## Prerequisites

- Access to shared staging workspace and incident channel
- Platform admin token with `admin` role
- Tenant business profile (name, slug, owner email)

## Day 0 Setup

1. Provision tenant with `POST /v1/admin/provision`.
2. Store the returned API key in your secret manager.
3. Set tenant-specific plan limits if required in tenant settings.
4. Confirm auth with `GET /v1/auth/me`.

## Day 1 Verification Checklist

1. Create lead/session/message and confirm timeline updates.
2. Trigger AI scoring and verify lead score changes.
3. Verify routing rule and sequence execution.
4. Validate integration hooks and webhook endpoint access.
5. Confirm `/metrics`, `/healthz`, and `/readyz` are healthy.

## Security Checklist

- Rotate API keys after initial provisioning
- Verify audit entries for admin/provision actions
- Enforce tenant header consistency in client gateways

## Handoff Pack

- Tenant ID
- Owner user ID
- API key fingerprint (prefix only)
- Selected plan and limit profile
- Runbook links and escalation contacts
