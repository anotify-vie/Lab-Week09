from pathlib import Path
from io import StringIO

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlmodel import Session

from app import database
from app.models import Hero, User
from app.security import hash_password


def migration_database(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setattr(database, "DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    return config, create_engine(url)


def test_fresh_database_upgrade_and_orm_round_trip(tmp_path, monkeypatch):
    config, engine = migration_database(tmp_path, monkeypatch)
    try:
        command.upgrade(config, "head")
        with Session(engine) as session:
            user = User(username="alice", hashed_password=hash_password("password123"))
            session.add(user)
            session.commit()
            session.refresh(user)
            hero = Hero(name="New hero", secret_name="Secret", owner_id=user.id)
            session.add(hero)
            session.commit()
            session.refresh(hero)
            assert hero.owner_id == user.id
            assert hero.status == "active"
            assert hero.created_at is not None
        assert {"hero", "team", "mission", "heromissionlink", "user", "alembic_version"} == set(inspect(engine).get_table_names())
        command.downgrade(config, "base")
        assert inspect(engine).get_table_names() == ["alembic_version"]
    finally:
        engine.dispose()


def test_upgrade_preserves_legacy_heroes_teams_and_missions(tmp_path, monkeypatch):
    config, engine = migration_database(tmp_path, monkeypatch)
    try:
        command.upgrade(config, "4158b1105b0d")
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO team (id, name, headquarters) VALUES (1, 'Avengers', 'NY')"))
            connection.execute(text("INSERT INTO mission (id, title) VALUES (1, 'Rescue')"))
            connection.execute(text("INSERT INTO hero (id, name, secret_name, team_id, power, status) VALUES (1, 'Legacy', 'Secret', 1, 'Speed', NULL)"))
            connection.execute(text("INSERT INTO heromissionlink (hero_id, mission_id) VALUES (1, 1)"))
        command.upgrade(config, "head")
        with Session(engine) as session:
            hero = session.get(Hero, 1)
            assert hero.name == "Legacy"
            assert hero.status == "active"
            assert hero.power == "Speed"
            assert hero.owner_id is None
            assert hero.created_at is not None
            assert hero.team.name == "Avengers"
            assert [mission.title for mission in hero.missions] == ["Rescue"]
        assert not next(column for column in inspect(engine).get_columns("hero") if column["name"] == "status")["nullable"]
        # Rolling back just the auth migration keeps the old hero and its links.
        command.downgrade(config, "4158b1105b0d")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT name FROM hero WHERE id=1")).scalar_one() == "Legacy"
            assert connection.execute(text("SELECT count(*) FROM heromissionlink")).scalar_one() == 1
        command.upgrade(config, "head")
    finally:
        engine.dispose()


def test_postgresql_upgrade_sql_has_enum_and_ownership_ddl(monkeypatch):
    # Validate PostgreSQL DDL without connecting to a real/user database.
    monkeypatch.setattr(database, "DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    output = StringIO()
    config = Config(
        str(Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=output
    )
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert sql.count("CREATE TYPE herostatus AS ENUM ('active', 'retired')") == 1
    assert sql.count("CREATE TYPE role AS ENUM ('user', 'admin')") == 1
    assert 'CREATE TABLE "user"' in sql
    assert "FOREIGN KEY(owner_id)" in sql
    assert "ALTER COLUMN status SET NOT NULL" in sql
