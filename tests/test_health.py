def test_healthz_ok(client) -> None:  # noqa: ANN001
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_requires_auth(client) -> None:  # noqa: ANN001
    response = client.get("/v1/auth/me")
    assert response.status_code == 401
