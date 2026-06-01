import asyncio

from conftest import auth_headers

from app.routing.pipeline import process_routing_event
from app.sequence.pipeline import process_sequence_step_event


def test_routing_rules_deterministic_assignment(client) -> None:  # noqa: ANN001
    headers = auth_headers("tenant-route")

    lead_resp = client.post(
        "/v1/leads",
        json={"name": "Dana", "email": "dana@example.com", "lead_score": 85},
        headers=headers,
    )
    assert lead_resp.status_code == 200
    lead_id = lead_resp.json()["lead"]["id"]

    low_rule = client.post(
        "/v1/routing/rules",
        json={
            "name": "Queue fallback",
            "priority": 10,
            "enabled": True,
            "conditions": [{"field": "lead_score", "op": "gte", "value": 50}],
            "action": "queue",
            "action_payload": {"queue_name": "general"},
        },
        headers=headers,
    )
    assert low_rule.status_code == 200

    high_rule = client.post(
        "/v1/routing/rules",
        json={
            "name": "Enterprise owner",
            "priority": 90,
            "enabled": True,
            "conditions": [{"field": "lead_score", "op": "gte", "value": 80}],
            "action": "assign_user",
            "action_payload": {"user_id": "user-enterprise"},
        },
        headers=headers,
    )
    assert high_rule.status_code == 200

    asyncio.run(
        process_routing_event(
            {
                "event": "lead.score_updated",
                "tenant_id": "tenant-route",
                "lead_id": lead_id,
            }
        )
    )

    lead_get = client.get(f"/v1/leads/{lead_id}", headers=headers)
    assert lead_get.status_code == 200
    body = lead_get.json()
    assert body["owner_user_id"] == "user-enterprise"
    assert body["assigned_queue_name"] is None


def test_sequence_enrollment_and_execution_records_timeline(client) -> None:  # noqa: ANN001
    headers = auth_headers("tenant-seq")

    lead_resp = client.post(
        "/v1/leads",
        json={"name": "Mia", "email": "mia@example.com", "phone": "+15550001111"},
        headers=headers,
    )
    assert lead_resp.status_code == 200
    lead_id = lead_resp.json()["lead"]["id"]

    seq_resp = client.post(
        "/v1/sequences",
        json={
            "name": "Welcome sequence",
            "description": "First touch",
            "trigger": "lead_created",
            "status": "active",
        },
        headers=headers,
    )
    assert seq_resp.status_code == 200
    sequence_id = seq_resp.json()["id"]

    step_resp = client.post(
        f"/v1/sequences/{sequence_id}/steps",
        json={
            "order_index": 0,
            "type": "email",
            "delay_seconds": 0,
            "template": "Hi {{name}}, thanks for your interest.",
        },
        headers=headers,
    )
    assert step_resp.status_code == 200

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
                "tenant_id": "tenant-seq",
                "enrollment_id": enrollment_id,
            }
        )
    )

    timeline_resp = client.get(f"/v1/leads/{lead_id}/timeline", headers=headers)
    assert timeline_resp.status_code == 200
    events = timeline_resp.json()
    assert any(event["type"] == "sequence_step_executed" for event in events)
