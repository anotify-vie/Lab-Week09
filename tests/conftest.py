import os

# Set these BEFORE importing the application; tests never use the real database/key.
os.environ["SECRET_KEY"] = "test-only-secret-never-use-in-production"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.main as main_module
from app.database import get_session
from app.models import Role, User
from app.security import hash_password


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine, monkeypatch):
    # Exercise the real lifespan while keeping all database I/O in memory.
    monkeypatch.setattr(main_module, "engine", engine)

    def override_session():
        with Session(engine) as session:
            yield session

    main_module.app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(main_module.app) as client:
            yield client
    finally:
        main_module.app.dependency_overrides.clear()


@pytest.fixture
def make_user(session):
    def make(username="alice", password="password123", role=Role.user):
        user = User(
            username=username, hashed_password=hash_password(password), role=role
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    return make


@pytest.fixture
def login(client, make_user):
    def sign_in(username="alice", password="password123", role=Role.user):
        make_user(username, password, role)
        response = client.post(
            "/api/v1/token", data={"username": username, "password": password}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    return sign_in
