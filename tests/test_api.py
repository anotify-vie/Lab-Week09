import pytest

from app.models import Role

API = "/api/v1"
HERO = {"name": "Deadpond", "secret_name": "Dive Wilson"}


@pytest.mark.parametrize("query", ["offset=-1", "limit=-1", "limit=0", "limit=101", "min_age=-1"])
def test_pagination_and_filter_validation(client, query):
    assert client.get(f"{API}/heroes?{query}").status_code == 422


@pytest.mark.parametrize("changes", [{"name": ""}, {"age": -1}, {"age": 1001}, {"status": "unknown"}])
def test_create_hero_validation(client, login, changes):
    assert client.post(f"{API}/heroes", json={**HERO, **changes}, headers=login()).status_code == 422


@pytest.mark.parametrize("field", ["name", "secret_name", "status"])
def test_patch_rejects_null_required_fields(client, login, field):
    headers = login()
    hero = client.post(f"{API}/heroes", json=HERO, headers=headers).json()
    assert client.patch(f"{API}/heroes/{hero['id']}", json={field: None}, headers=headers).status_code == 422


def test_team_validation_filters_and_nullable_patch_fields(client, login):
    headers = login("root", role=Role.admin)
    assert client.post(f"{API}/heroes", json={**HERO, "team_id": 999}, headers=headers).status_code == 400
    team = client.post(f"{API}/teams", json={"name": "Avengers", "headquarters": "NY"}, headers=headers).json()
    first = client.post(f"{API}/heroes", json={**HERO, "age": 30, "team_id": team["id"], "power": "Speed"}, headers=headers).json()
    second = client.post(f"{API}/heroes", json={**HERO, "name": "Other", "age": 10}, headers=headers).json()
    filtered = client.get(f"{API}/heroes?min_age=20&team_id={team['id']}&name=DEAD").json()
    assert [hero["id"] for hero in filtered] == [first["id"]]
    assert client.get(f"{API}/heroes?offset=1&limit=1").json()[0]["id"] == second["id"]
    path = f"{API}/heroes/{first['id']}"
    assert client.patch(path, json={"team_id": 999}, headers=headers).status_code == 400
    response = client.patch(path, json={"team_id": None, "age": None, "power": None}, headers=headers)
    assert response.status_code == 200
    assert all(response.json()[field] is None for field in ("team_id", "age", "power"))


def test_swagger_oauth_configuration_and_frontend_assets(client):
    schema = client.get("/openapi.json").json()
    flow = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]
    assert flow["tokenUrl"] == "/api/v1/token"
    assert "security" not in schema["paths"][f"{API}/heroes"]["get"]
    assert schema["paths"][f"{API}/heroes"]["post"]["security"]
    assert {"401", "403", "409"} <= schema["paths"][f"{API}/teams"]["post"]["responses"].keys()
    for path in ("/frontend/", "/frontend/app.js", "/frontend/styles.css"):
        assert client.get(path).status_code == 200


def test_openapi_documents_rest_contract_examples_and_errors(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 200
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "Heroes API"
    assert schema["info"]["version"]
    models = schema["components"]["schemas"]
    assert models["HeroStatus"]["enum"] == ["active", "retired"]
    assert models["HeroCreate"]["properties"]["name"]["examples"] == ["Deadpond"]
    assert models["HeroUpdate"]["properties"]["status"]["examples"] == ["retired"]
    assert "created_at" not in models["HeroCreate"]["properties"]
    assert "secret_name" not in models["HeroPublic"]["properties"]
    for path, operations in schema["paths"].items():
        if not path.startswith(API):
            continue
        for operation in operations.values():
            assert operation["tags"]
            assert operation["summary"]
    assert "404" in schema["paths"][f"{API}/heroes/{{hero_id}}"]["get"]["responses"]
    assert "400" in schema["paths"][f"{API}/heroes"]["post"]["responses"]
    assert "404" in schema["paths"][f"{API}/teams/{{team_id}}/heroes"]["get"]["responses"]
