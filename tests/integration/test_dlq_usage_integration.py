import asyncio

import pytest
from conftest import auth_headers

from app.db.session import AsyncSessionLocal
from app.models.failed_job import FailedJob


@pytest.mark.integration
def test_admin_dlq_list_and_replay(client) -> None:  # noqa: ANN001
    """Seed a failed job, verify it appears in GET /admin/dlq, replay it."""

    async def _seed() -> str:
        async with AsyncSessionLocal() as db:
            job = FailedJob(
                queue_name="ai_jobs",
                event_type="message.created",
                payload={"event": "message.created", "tenant_id": "t1", "message_id": "m1"},
                error="connection refused",
                attempts=3,
                status="pending",
                tenant_id="t1",
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
            return str(job.id)

    job_id = asyncio.run(_seed())

    headers = auth_headers("tenant-admin", role="admin")

    # List DLQ — should see our job
    list_resp = client.get("/v1/admin/dlq", headers=headers)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["total"] >= 1
    ids = [j["id"] for j in body["jobs"]]
    assert job_id in ids

    # Replay the job — SQS is unconfigured so publish no-ops but status updates
    replay_resp = client.post(f"/v1/admin/dlq/{job_id}/replay", headers=headers)
    assert replay_resp.status_code == 200
    rdata = replay_resp.json()
    assert rdata["replayed"] is True
    assert rdata["job_id"] == job_id


@pytest.mark.integration
def test_admin_usage_endpoint(client) -> None:  # noqa: ANN001
    """Provision a tenant then verify the usage endpoint returns a valid response."""
    headers = auth_headers("tenant-admin", role="admin")

    prov_resp = client.post(
        "/v1/admin/provision",
        json={
            "name": "Usage Test Tenant",
            "slug": "usage-test-tenant",
            "owner_email": "owner@usagetest.com",
            "plan": "growth",
        },
        headers=headers,
    )
    assert prov_resp.status_code == 200
    tenant_id = prov_resp.json()["tenant_id"]

    usage_resp = client.get(
        f"/v1/admin/tenants/{tenant_id}/usage?days=7",
        headers=headers,
    )
    assert usage_resp.status_code == 200
    udata = usage_resp.json()
    assert udata["tenant_id"] == tenant_id
    assert udata["days"] == 7
    assert isinstance(udata["records"], list)
