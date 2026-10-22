import pytest


@pytest.mark.parametrize("origin", ["http://localhost:5500", "http://127.0.0.1:5500"])
def test_live_server_can_read_public_heroes(client, origin):
    response = client.get("/api/v1/heroes", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "Origin" in response.headers["vary"]
    assert "access-control-allow-credentials" not in response.headers


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
def test_preflight_allows_json_and_bearer_headers_without_login(client, method):
    response = client.options("/api/v1/heroes", headers={
        "Origin": "http://127.0.0.1:5500",
        "Access-Control-Request-Method": method,
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5500"
    assert method in response.headers["access-control-allow-methods"]
    assert response.headers["access-control-allow-headers"] == "authorization,content-type"


@pytest.mark.parametrize("origin", ["https://untrusted.example", "http://localhost:5501"])
def test_unlisted_origin_has_no_cors_access(client, origin):
    response = client.get("/api/v1/heroes", headers={"Origin": origin})
    # CORS is a browser rule: the API still responds, without permission to read it.
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
    preflight = client.options("/api/v1/heroes", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers


def test_authentication_errors_are_readable_by_allowed_frontend(client):
    response = client.post("/api/v1/heroes", json={
        "name": "Hero", "secret_name": "Secret",
    }, headers={"Origin": "http://localhost:5500"})
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:5500"


def test_same_origin_request_needs_no_cors_headers(client):
    response = client.get("/api/v1/heroes")
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
