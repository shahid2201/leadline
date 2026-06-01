import asyncio

from conftest import auth_headers

from app.ai.pipeline import process_message_created_event


def test_message_ai_processing_and_lead_scoring(client) -> None:  # noqa: ANN001
    headers = auth_headers("tenant-ai")

    lead_resp = client.post(
        "/v1/leads",
        json={"name": "Sam", "email": "sam@example.com", "phone": "+15555550123"},
        headers=headers,
    )
    assert lead_resp.status_code == 200
    lead_id = lead_resp.json()["lead"]["id"]

    session_resp = client.post(
        "/v1/sessions",
        json={"visitor_id": "visitor-ai", "lead_id": lead_id, "metadata": {"page_url": "https://x"}},
        headers=headers,
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["id"]

    message_resp = client.post(
        f"/v1/sessions/{session_id}/messages",
        json={
            "sender_type": "visitor",
            "content": "Need pricing for our 50 person team this month",
        },
        headers=headers,
    )
    assert message_resp.status_code == 200
    message_id = message_resp.json()["id"]

    asyncio.run(
        process_message_created_event(
            {
                "event": "message.created",
                "tenant_id": "tenant-ai",
                "session_id": session_id,
                "message_id": message_id,
            }
        )
    )

    message_get = client.get(f"/v1/messages/{message_id}", headers=headers)
    assert message_get.status_code == 200
    message_body = message_get.json()
    assert message_body["intent"] is not None
    assert message_body["urgency"] in {"low", "medium", "high"}
    assert isinstance(message_body["entities"], dict)

    lead_get = client.get(f"/v1/leads/{lead_id}", headers=headers)
    assert lead_get.status_code == 200
    lead_body = lead_get.json()
    assert lead_body["fit_score"] >= 0
    assert lead_body["engagement_score"] >= 0
    assert lead_body["lead_score"] >= 0

    timeline_list = client.get(f"/v1/leads/{lead_id}/timeline", headers=headers)
    assert timeline_list.status_code == 200
    events = timeline_list.json()
    assert any(event["type"] == "ai_scored" for event in events)
