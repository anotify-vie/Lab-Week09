import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from sqlmodel import select

from app.models import User
from app.security import ALGORITHM, SECRET_KEY, hash_password, verify_password

API = "/api/v1"
PASSWORD = "password123"


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_stores_hash_and_never_returns_password(client, session):
    response = client.post(f"{API}/register", json={
        "username": "alice", "password": PASSWORD, "role": "admin",
        "hashed_password": "attacker-supplied-hash",
    })
    assert response.status_code == 201
    assert response.json() == {"id": 1, "username": "alice", "role": "user"}
    user = session.exec(select(User)).one()
    assert user.hashed_password.startswith("$2b$")
    assert user.hashed_password != PASSWORD
    assert verify_password(PASSWORD, user.hashed_password)


def test_same_password_has_different_salts(client, session):
    for username in ("alice", "bobby"):
        assert client.post(f"{API}/register", json={"username": username, "password": PASSWORD}).status_code == 201
    users = session.exec(select(User).order_by(User.id)).all()
    assert users[0].hashed_password != users[1].hashed_password
    assert all(verify_password(PASSWORD, user.hashed_password) for user in users)
    assert not verify_password("Password123", users[0].hashed_password)


def test_duplicate_username_returns_409_and_session_recovers(client):
    body = {"username": "alice", "password": PASSWORD}
    assert client.post(f"{API}/register", json=body).status_code == 201
    response = client.post(f"{API}/register", json=body)
    assert response.status_code == 409
    assert response.json()["detail"] == "Username already taken"
    assert client.post(f"{API}/register", json={**body, "username": "bobby"}).status_code == 201


@pytest.mark.parametrize("changes", [
    {"username": "ab"}, {"username": "a" * 31}, {"password": "short"},
    {"password": "a" * 73}, {"password": "ể" * 25}, {"password": None},
])
def test_registration_validation(client, changes):
    response = client.post(f"{API}/register", json={"username": "alice", "password": PASSWORD, **changes})
    assert response.status_code == 422


@pytest.mark.parametrize("password", ["a" * 72, "ể" * 24])
def test_72_byte_password_is_accepted_and_can_log_in(client, password):
    assert client.post(f"{API}/register", json={"username": "alice", "password": password}).status_code == 201
    assert client.post(f"{API}/token", data={"username": "alice", "password": password}).status_code == 200


def test_login_returns_short_lived_token_with_no_secrets(client, make_user):
    user = make_user()
    response = client.post(f"{API}/token", data={"username": "alice", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    token = response.json()["access_token"]
    assert len(token.split(".")) == 3
    encoded = token.split(".")[1]
    payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    assert set(payload) == {"sub", "exp"}
    assert payload["sub"] == str(user.id)
    assert 29 * 60 < payload["exp"] - datetime.now(timezone.utc).timestamp() <= 30 * 60
    assert jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) == payload
    me = client.get(f"{API}/me", headers=bearer(token))
    assert me.status_code == 200
    assert me.json() == {"id": user.id, "username": "alice", "role": "user"}


@pytest.mark.parametrize("username,password", [
    ("alice", "wrong-password"), ("missing", PASSWORD),
    ("' OR '1'='1", PASSWORD), ("alice", "a" * 73),
])
def test_bad_login_is_401_with_same_message(client, make_user, username, password):
    make_user()
    response = client.post(f"{API}/token", data={"username": username, "password": password})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
    assert response.headers["www-authenticate"] == "Bearer"


def test_token_endpoint_requires_form_not_json(client):
    assert client.post(f"{API}/token", json={"username": "alice", "password": PASSWORD}).status_code == 422


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic abc"}, bearer("garbage"), bearer("")])
def test_me_rejects_missing_or_invalid_authentication(client, headers):
    response = client.get(f"{API}/me", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("case", [
    "expired", "wrong-key", "wrong-algorithm", "missing-exp", "missing-sub",
    "invalid-sub", "null-sub", "huge-sub", "unknown-user", "tampered",
])
def test_invalid_jwt_is_401(client, make_user, case):
    user = make_user()
    payload = {"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    key, algorithm = SECRET_KEY, ALGORITHM
    if case == "expired":
        payload["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    elif case == "wrong-key":
        key = "another-signing-key"
    elif case == "wrong-algorithm":
        algorithm = "HS512"
    elif case == "missing-exp":
        del payload["exp"]
    elif case == "missing-sub":
        del payload["sub"]
    elif case == "invalid-sub":
        payload["sub"] = "not-an-integer"
    elif case == "null-sub":
        payload["sub"] = None
    elif case == "huge-sub":
        payload["sub"] = str(2**100)
    elif case == "unknown-user":
        payload["sub"] = "9999"
    token = jwt.encode(payload, key, algorithm=algorithm)
    if case == "tampered":
        head, body, signature = token.split(".")
        changed = {"sub": "9999", "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())}
        body = base64.urlsafe_b64encode(json.dumps(changed).encode()).decode().rstrip("=")
        token = f"{head}.{body}.{signature}"
    response = client.get(f"{API}/me", headers=bearer(token))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_deleted_user_cannot_reuse_token(client, login, session):
    headers = login()
    user = session.exec(select(User)).one()
    session.delete(user)
    session.commit()
    assert client.get(f"{API}/me", headers=headers).status_code == 401


def test_bcrypt_does_not_accept_truncated_long_password():
    hashed = hash_password("a" * 72)
    assert not verify_password("a" * 73, hashed)
    with pytest.raises(ValueError):
        hash_password("a" * 73)
