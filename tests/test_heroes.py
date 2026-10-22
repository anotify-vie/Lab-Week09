from datetime import datetime, timezone

import pytest

API = "/api/v1/heroes"
HERO = {"name": "Deadpond", "secret_name": "Dive Wilson", "age": 45}


def test_list_heroes_starts_empty(client):
    response = client.get(API)
    assert response.status_code == 200
    assert response.json() == []


def test_create_read_and_list_share_public_json_and_utc_timestamp(client, login):
    headers = login()
    before = datetime.now(timezone.utc)
    response = client.post(API, json={**HERO, "created_at": "2000-01-01T00:00:00Z"}, headers=headers)
    assert response.status_code == 201
    hero = response.json()
    assert hero["status"] == "active"
    assert "secret_name" not in hero
    created_at = datetime.fromisoformat(hero["created_at"].replace("Z", "+00:00"))
    assert created_at.tzinfo is not None
    assert created_at.utcoffset().total_seconds() == 0
    assert before <= created_at <= datetime.now(timezone.utc)
    detail = client.get(f"{API}/{hero['id']}")
    assert detail.status_code == 200
    assert detail.json() == hero
    assert client.get(API).json() == [hero]


def test_read_missing_hero_has_standard_error(client):
    response = client.get(f"{API}/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Hero not found"}


@pytest.mark.parametrize("payload,field", [
    ({}, "name"), ({"name": "X"}, "secret_name"),
    ({**HERO, "age": "old"}, "age"), ({**HERO, "name": "x" * 51}, "name"),
])
def test_invalid_create_identifies_field_in_422(client, login, payload, field):
    response = client.post(API, json=payload, headers=login())
    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])


def test_patch_changes_only_sent_fields_and_preserves_creation_time(client, login):
    headers = login()
    hero = client.post(API, json=HERO, headers=headers).json()
    path = f"{API}/{hero['id']}"
    response = client.patch(path, json={"status": "retired"}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {**hero, "status": "retired"}
    unchanged = client.patch(path, json={}, headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json() == response.json()


@pytest.mark.parametrize("changes,field", [
    ({"age": "old"}, "age"), ({"age": -5}, "age"),
    ({"age": 1001}, "age"), ({"name": ""}, "name"),
    ({"name": "x" * 51}, "name"), ({"status": "dead"}, "status"),
])
def test_invalid_patch_is_422_and_keeps_original_hero(client, login, changes, field):
    headers = login()
    hero = client.post(API, json=HERO, headers=headers).json()
    path = f"{API}/{hero['id']}"
    response = client.patch(path, json=changes, headers=headers)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
    assert client.get(path).json() == hero


def test_non_integer_hero_id_is_422(client):
    response = client.get(f"{API}/not-an-id")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "hero_id"]
