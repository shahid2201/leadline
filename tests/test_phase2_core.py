from conftest import auth_headers


def test_lead_dedup_and_tenant_isolation(client) -> None:  # noqa: ANN001
    tenant_1_headers = auth_headers("tenant-1")
    tenant_2_headers = auth_headers("tenant-2")

    create_payload = {
        "name": "Sarah",
        "email": "Sarah@Example.com",
        "phone": "+1 (555) 123-4567",
        "company": "BrightTech",
    }

    first = client.post("/v1/leads", json=create_payload, headers=tenant_1_headers)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["deduplicated"] is False
    first_lead_id = first_body["lead"]["id"]

    second = client.post("/v1/leads", json=create_payload, headers=tenant_1_headers)
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["deduplicated"] is True
    assert second_body["lead"]["id"] == first_lead_id

    tenant_2_list = client.get("/v1/leads", headers=tenant_2_headers)
    assert tenant_2_list.status_code == 200
    assert tenant_2_list.json() == []

    tenant_2_get = client.get(f"/v1/leads/{first_lead_id}", headers=tenant_2_headers)
    assert tenant_2_get.status_code == 404


def test_sessions_messages_timeline_and_attach_flow(client) -> None:  # noqa: ANN001
    headers = auth_headers("tenant-a")

    lead_resp = client.post(
        "/v1/leads",
        json={"name": "Alex", "email": "alex@example.com", "phone": "+15551230000"},
        headers=headers,
    )
    assert lead_resp.status_code == 200
    lead_id = lead_resp.json()["lead"]["id"]

    session_resp = client.post(
        "/v1/sessions",
        json={"visitor_id": "visitor-1", "metadata": {"page_url": "https://example.com"}},
        headers=headers,
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["id"]

    message_resp = client.post(
        f"/v1/sessions/{session_id}/messages",
        json={"sender_type": "visitor", "content": "Need pricing for 50 seats"},
        headers=headers,
    )
    assert message_resp.status_code == 200
    message_id = message_resp.json()["id"]

    messages_list = client.get(f"/v1/sessions/{session_id}/messages", headers=headers)
    assert messages_list.status_code == 200
    assert len(messages_list.json()) == 1

    attach_resp = client.post(
        f"/v1/leads/{lead_id}/attach-session",
        json={"session_id": session_id},
        headers=headers,
    )
    assert attach_resp.status_code == 200

    session_get = client.get(f"/v1/sessions/{session_id}", headers=headers)
    assert session_get.status_code == 200
    assert session_get.json()["lead_id"] == lead_id

    timeline_create = client.post(
        f"/v1/leads/{lead_id}/timeline",
        json={"type": "note", "payload": {"text": "high intent"}},
        headers=headers,
    )
    assert timeline_create.status_code == 200
    event_id = timeline_create.json()["id"]

    timeline_get = client.get(f"/v1/timeline/{event_id}", headers=headers)
    assert timeline_get.status_code == 200

    timeline_patch = client.patch(
        f"/v1/timeline/{event_id}",
        json={"payload": {"text": "qualified"}},
        headers=headers,
    )
    assert timeline_patch.status_code == 200
    assert timeline_patch.json()["payload"]["text"] == "qualified"

    message_patch = client.patch(
        f"/v1/messages/{message_id}",
        json={"content": "Need pricing this month"},
        headers=headers,
    )
    assert message_patch.status_code == 200
    assert message_patch.json()["content"] == "Need pricing this month"

    message_delete = client.delete(f"/v1/messages/{message_id}", headers=headers)
    assert message_delete.status_code == 204
    message_get = client.get(f"/v1/messages/{message_id}", headers=headers)
    assert message_get.status_code == 404

    timeline_delete = client.delete(f"/v1/timeline/{event_id}", headers=headers)
    assert timeline_delete.status_code == 204
    timeline_missing = client.get(f"/v1/timeline/{event_id}", headers=headers)
    assert timeline_missing.status_code == 404
