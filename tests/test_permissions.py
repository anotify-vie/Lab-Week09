import pytest
from sqlmodel import select

from app.models import Hero, Role, User

API = "/api/v1"
HERO = {"name": "Deadpond", "secret_name": "Dive Wilson"}
TEAM = {"name": "Avengers", "headquarters": "New York"}


@pytest.mark.parametrize("method,path,body", [
    ("POST", "/heroes", HERO), ("PATCH", "/heroes/1", {"age": 30}),
    ("DELETE", "/heroes/1", None), ("POST", "/teams", TEAM),
    ("POST", "/missions", {"title": "Rescue"}),
    ("POST", "/heroes/1/missions/1", None),
])
@pytest.mark.parametrize("prefix", [API, ""])
def test_all_writes_require_login_including_legacy_urls(client, method, path, body, prefix):
    response = client.request(method, f"{prefix}{path}", json=body)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_reads_remain_public(client, login):
    headers = login("root", role=Role.admin)
    team = client.post(f"{API}/teams", json=TEAM, headers=headers).json()
    hero = client.post(f"{API}/heroes", json={**HERO, "team_id": team["id"]}, headers=headers).json()
    for path in ("/heroes", f"/heroes/{hero['id']}", "/teams", f"/teams/{team['id']}/heroes", f"/heroes/{hero['id']}/missions"):
        response = client.get(f"{API}{path}")
        assert response.status_code == 200
        assert "Dive Wilson" not in response.text


def test_server_sets_owner_and_does_not_expose_secret_name(client, login):
    headers = login()
    me = client.get(f"{API}/me", headers=headers).json()
    response = client.post(f"{API}/heroes", json={**HERO, "owner_id": 9999}, headers=headers)
    assert response.status_code == 201
    assert response.json()["owner_id"] == me["id"]
    assert response.json()["status"] == "active"
    assert response.json()["created_at"]
    assert "secret_name" not in response.json()


def test_owner_can_patch_then_delete_and_cannot_transfer_ownership(client, login):
    headers = login()
    hero = client.post(f"{API}/heroes", json=HERO, headers=headers).json()
    response = client.patch(f"{API}/heroes/{hero['id']}", json={"age": 42, "owner_id": 9999}, headers=headers)
    assert response.status_code == 200
    assert response.json()["age"] == 42
    assert response.json()["owner_id"] == hero["owner_id"]
    response = client.delete(f"{API}/heroes/{hero['id']}", headers=headers)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"{API}/heroes/{hero['id']}").status_code == 404


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_other_user_cannot_modify_hero(client, login, method):
    alice, bob = login("alice"), login("bobby")
    hero = client.post(f"{API}/heroes", json=HERO, headers=alice).json()
    path = f"{API}/heroes/{hero['id']}"
    response = client.request(method, path, json={"name": "Stolen"}, headers=bob)
    assert response.status_code == 403
    assert client.get(path).json()["name"] == HERO["name"]


def test_admin_can_modify_and_delete_another_users_hero(client, login):
    alice, admin = login("alice"), login("root", role=Role.admin)
    hero = client.post(f"{API}/heroes", json=HERO, headers=alice).json()
    path = f"{API}/heroes/{hero['id']}"
    assert client.patch(path, json={"status": "retired"}, headers=admin).status_code == 200
    assert client.delete(path, headers=admin).status_code == 204


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_missing_hero_returns_404_for_authenticated_user(client, login, method):
    response = client.request(method, f"{API}/heroes/999", json={"age": 30}, headers=login())
    assert response.status_code == 404


def test_only_admin_creates_teams_and_duplicate_is_409(client, login):
    alice, admin = login("alice"), login("root", role=Role.admin)
    assert client.post(f"{API}/teams", json=TEAM, headers=alice).status_code == 403
    assert client.post(f"{API}/teams", json=TEAM, headers=admin).status_code == 201
    assert client.post(f"{API}/teams", json=TEAM, headers=admin).status_code == 409


def test_role_is_reloaded_from_database_not_token(client, login, session):
    headers = login("root", role=Role.admin)
    user = session.exec(select(User)).one()
    user.role = Role.user
    session.add(user)
    session.commit()
    assert client.post(f"{API}/teams", json=TEAM, headers=headers).status_code == 403


def test_unowned_legacy_hero_is_admin_only(client, login, session):
    legacy = Hero(name="Legacy", secret_name="Old hero")
    session.add(legacy)
    session.commit()
    session.refresh(legacy)
    path = f"{API}/heroes/{legacy.id}"
    assert client.patch(path, json={"age": 10}, headers=login()).status_code == 403
    assert client.delete(path, headers=login("root", role=Role.admin)).status_code == 204


def test_mission_assignment_requires_hero_owner_and_is_idempotent(client, login):
    alice, bob = login("alice"), login("bobby")
    hero = client.post(f"{API}/heroes", json=HERO, headers=alice).json()
    mission_response = client.post(f"{API}/missions", json={"title": "Rescue"}, headers=bob)
    assert mission_response.status_code == 201
    mission = mission_response.json()
    path = f"{API}/heroes/{hero['id']}/missions/{mission['id']}"
    assert client.post(path, headers=bob).status_code == 403
    assert client.post(path, headers=alice).status_code == 204
    assert client.post(path, headers=alice).status_code == 204
    assert client.get(f"{API}/heroes/{hero['id']}/missions").json() == [mission]
    # Deleting an assigned hero must also remove the link row with FK checks on.
    assert client.delete(f"{API}/heroes/{hero['id']}", headers=alice).status_code == 204


def test_legacy_and_versioned_urls_use_same_data_and_permissions(client, login):
    headers = login()
    hero = client.post("/heroes", json=HERO, headers=headers).json()
    assert client.get(f"{API}/heroes/{hero['id']}").json() == hero
    assert client.delete(f"/heroes/{hero['id']}", headers=headers).status_code == 204
