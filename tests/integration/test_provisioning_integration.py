import pytest
from conftest import auth_headers


@pytest.mark.integration
def test_admin_provision_tenant_flow(client) -> None:  # noqa: ANN001
    headers = auth_headers("tenant-admin", role="admin")
    response = client.post(
        "/v1/admin/provision",
        json={
            "name": "Design Partner One",
            "slug": "design-partner-one",
            "owner_email": "owner@partner.test",
            "plan": "starter",
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"]
    assert body["user_id"]
    assert body["api_key"].startswith("ll_live_")
