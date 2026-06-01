from conftest import auth_headers


def test_metrics_endpoint_available_without_auth(client) -> None:  # noqa: ANN001
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "leadline_api_requests_total" in response.text


def test_rbac_blocks_non_admin_routing_rule_create(client) -> None:  # noqa: ANN001
    headers = auth_headers("tenant-sec", role="viewer")
    response = client.post(
        "/v1/routing/rules",
        json={
            "name": "Viewer cannot create",
            "priority": 10,
            "enabled": True,
            "conditions": [{"field": "lead_score", "op": "gte", "value": 10}],
            "action": "queue",
            "action_payload": {"queue_name": "general"},
        },
        headers=headers,
    )
    assert response.status_code == 403


def test_tenant_header_mismatch_rejected(client) -> None:  # noqa: ANN001
    headers = auth_headers("tenant-a", role="admin")
    headers["X-Tenant-ID"] = "tenant-b"
    response = client.get("/v1/leads", headers=headers)
    assert response.status_code == 403
