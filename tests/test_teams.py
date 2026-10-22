import pytest

from app.models import Role

API = "/api/v1"
TEAM = {"name": "Avengers", "headquarters": "New York"}


def test_list_teams_starts_empty(client):
    response = client.get(f"{API}/teams")
    assert response.status_code == 200
    assert response.json() == []


def test_create_team_response_and_duplicate_conflict(client, login):
    headers = login("root", role=Role.admin)
    response = client.post(f"{API}/teams", json=TEAM, headers=headers)
    assert response.status_code == 201
    team = response.json()
    assert team == {**TEAM, "id": team["id"]}
    assert client.get(f"{API}/teams").json() == [team]
    duplicate = client.post(f"{API}/teams", json=TEAM, headers=headers)
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Team name already exists"}
    assert client.post(f"{API}/teams", json={**TEAM, "name": "X-Men"}, headers=headers).status_code == 201


def test_team_heroes_excludes_other_teams_and_unknown_team_is_404(client, login):
    headers = login("root", role=Role.admin)
    teams = [client.post(f"{API}/teams", json={**TEAM, "name": name}, headers=headers).json() for name in ("Avengers", "X-Men")]
    empty = client.get(f"{API}/teams/{teams[0]['id']}/heroes")
    assert empty.status_code == 200
    assert empty.json() == []
    heroes = [client.post(f"{API}/heroes", json={
        "name": name, "secret_name": "Hidden", "team_id": team["id"],
    }, headers=headers).json() for name, team in zip(("Tony", "Logan"), teams)]
    for team, hero in zip(teams, heroes):
        response = client.get(f"{API}/teams/{team['id']}/heroes")
        assert response.status_code == 200
        assert response.json() == [hero]
        assert "secret_name" not in response.json()[0]
    unknown = client.get(f"{API}/teams/999/heroes")
    assert unknown.status_code == 404
    assert unknown.json() == {"detail": "Team not found"}
    # Filtering an unknown team is an empty collection, not a missing resource.
    assert client.get(f"{API}/heroes?team_id=999").json() == []


@pytest.mark.parametrize("body", [{}, {"name": "Avengers"}, {**TEAM, "name": ""}, {**TEAM, "name": "x" * 51}])
def test_invalid_team_body_is_422(client, login, body):
    response = client.post(f"{API}/teams", json=body, headers=login("root", role=Role.admin))
    assert response.status_code == 422
