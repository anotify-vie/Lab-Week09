import os
from pathlib import Path
import subprocess
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlmodel import Session, select

from app import database
from app.models import Role, User
from app.security import verify_password


def test_admin_cli_creates_admin_and_handles_duplicate_and_invalid_input(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'admin.db'}"
    monkeypatch.setattr(database, "DATABASE_URL", url)
    project = Path(__file__).resolve().parents[1]
    command.upgrade(Config(str(project / "alembic.ini")), "head")

    def run(username, password):
        return subprocess.run(
            [sys.executable, "-m", "app.create_admin", username, password],
            cwd=project, env={**os.environ, "DATABASE_URL": url},
            text=True, capture_output=True, timeout=15,
        )

    result = run("root", "password123")
    assert result.returncode == 0, result.stderr
    assert "created" in result.stdout
    assert "password123" not in result.stdout + result.stderr
    engine = create_engine(url)
    try:
        with Session(engine) as session:
            admin = session.exec(select(User)).one()
            assert admin.role == Role.admin
            assert verify_password("password123", admin.hashed_password)
        duplicate = run("root", "password123")
        assert duplicate.returncode == 1
        assert "Username already taken" in duplicate.stderr
        invalid = run("other", "short")
        assert invalid.returncode == 1
        assert "at least 8" in invalid.stderr
    finally:
        engine.dispose()
