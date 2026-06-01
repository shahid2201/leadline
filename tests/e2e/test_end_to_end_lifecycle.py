import asyncio

import pytest
from conftest import auth_headers

from app.ai.pipeline import process_message_created_event
from app.integrations.pipeline import process_integration_event
from app.routing.pipeline import process_routing_event
from app.sequence.pipeline import process_sequence_step_event, process_sequence_trigger_event


@pytest.mark.e2e
def test_full_lifecycle_e2e(client) -> None:  # noqa: ANN001
    headers = auth_headers("tenant-e2e", role="admin")

    rule_resp = client.post(
        "/v1/routing/rules",
        json={
            "name": "High score assign",
            "priority": 100,
            "enabled": True,
            "conditions": [{"field": "lead_score", "op": "gte", "value": 50}],
            "action": "assign_user",
            "action_payload": {"user_id": "rep-e2e"},
        },
        headers=headers,
    )
    assert rule_resp.status_code == 200

    seq_resp = client.post(
        "/v1/sequences",
        json={"name": "E2E sequence", "trigger": "score_updated", "status": "active"},
        headers=headers,
    )
    assert seq_resp.status_code == 200
    sequence_id = seq_resp.json()["id"]

    step_resp = client.post(
        f"/v1/sequences/{sequence_id}/steps",
        json={"order_index": 0, "type": "task", "delay_seconds": 0, "template": "Follow up"},
        headers=headers,
    )
    assert step_resp.status_code == 200

    lead_resp = client.post(
        "/v1/leads",
        json={"name": "E2E Lead", "email": "e2e@example.com", "phone": "+15550000001"},
        headers=headers,
    )
    assert lead_resp.status_code == 200
    lead_id = lead_resp.json()["lead"]["id"]

    session_resp = client.post(
        "/v1/sessions",
        json={"visitor_id": "visitor-e2e", "lead_id": lead_id, "metadata": {"page_url": "https://x"}},
        headers=headers,
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["id"]

    message_resp = client.post(
        f"/v1/sessions/{session_id}/messages",
        json={"sender_type": "visitor", "content": "Need pricing for 120 users this week"},
        headers=headers,
    )
    assert message_resp.status_code == 200
    message_id = message_resp.json()["id"]

    asyncio.run(
        process_message_created_event(
            {
                "event": "message.created",
                "tenant_id": "tenant-e2e",
                "session_id": session_id,
                "message_id": message_id,
            }
        )
    )
    asyncio.run(
        process_routing_event(
            {"event": "lead.score_updated", "tenant_id": "tenant-e2e", "lead_id": lead_id}
        )
    )
    asyncio.run(
        process_sequence_trigger_event(
            {
                "event": "sequence.trigger",
                "tenant_id": "tenant-e2e",
                "lead_id": lead_id,
                "trigger": "score_updated",
            }
        )
    )

    enroll_resp = client.post(
        f"/v1/sequences/{sequence_id}/enroll",
        json={"lead_id": lead_id},
        headers=headers,
    )
    assert enroll_resp.status_code == 200
    enrollment_id = enroll_resp.json()["id"]

    asyncio.run(
        process_sequence_step_event(
            {
                "event": "sequence.step.execute",
                "tenant_id": "tenant-e2e",
                "enrollment_id": enrollment_id,
            }
        )
    )
    asyncio.run(
        process_integration_event(
            {
                "event": "integration.lead.score_updated",
                "tenant_id": "tenant-e2e",
                "lead_id": lead_id,
            }
        )
    )

    lead_get = client.get(f"/v1/leads/{lead_id}", headers=headers)
    assert lead_get.status_code == 200
    assert lead_get.json()["owner_user_id"] == "rep-e2e"

    timeline = client.get(f"/v1/leads/{lead_id}/timeline", headers=headers)
    assert timeline.status_code == 200
    events = timeline.json()
    assert any(item["type"] == "ai_scored" for item in events)
    assert any(item["type"] == "sequence_step_executed" for item in events)
