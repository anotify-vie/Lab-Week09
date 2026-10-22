from sqlmodel import Field, Relationship, SQLModel
from enum import Enum
from datetime import datetime, timezone
from pydantic import field_validator
from sqlalchemy import DateTime


class Role(str, Enum):
    user = "user"
    admin = "admin"


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True, min_length=3, max_length=30)


class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    role: Role = Role.user
    heroes: list["Hero"] = Relationship(back_populates="owner")


class UserCreate(UserBase):
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class UserPublic(UserBase):
    id: int
    role: Role


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# =========================
# LINK TABLE
# =========================

class HeroMissionLink(SQLModel, table=True):
    hero_id: int | None = Field(
        default=None,
        foreign_key="hero.id",
        primary_key=True
    )

    mission_id: int | None = Field(
        default=None,
        foreign_key="mission.id",
        primary_key=True
    )


# =========================
# TEAM MODELS
# =========================

class TeamBase(SQLModel):
    name: str = Field(
        index=True,
        unique=True,
        min_length=1,
        max_length=50,
        schema_extra={"examples": ["Avengers"]}
    )

    headquarters: str = Field(
        schema_extra={"examples": ["New York"]}
    )


class Team(TeamBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    heroes: list["Hero"] = Relationship(back_populates="team")


class TeamCreate(TeamBase):
    pass


class TeamPublic(TeamBase):
    id: int


# =========================
# HERO MODELS
# =========================
class HeroStatus(str, Enum):
    active = "active"
    retired = "retired"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HeroBase(SQLModel):
    name: str = Field(
        index=True,
        min_length=1,
        max_length=50,
        schema_extra={"examples": ["Deadpond"]}
    )

    age: int | None = Field(
        default=None,
        ge=0,
        le=1000,
        schema_extra={"examples": [30]}
    )

    team_id: int | None = Field(
        default=None,
        foreign_key="team.id"
    )

    power: str | None = None

    status: HeroStatus = HeroStatus.active


class Hero(HeroBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    secret_name: str
    team: Team | None = Relationship(back_populates="heroes")
    missions: list["Mission"] = Relationship(
        back_populates="heroes",
        link_model=HeroMissionLink
    )
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    owner_id: int | None = Field(default=None, foreign_key="user.id")
    owner: User | None = Relationship(back_populates="heroes")


class HeroCreate(HeroBase):
    secret_name: str = Field(
        schema_extra={"examples": ["Dive Wilson"]}
    )


class HeroPublic(HeroBase):
    id: int
    created_at: datetime
    owner_id: int | None


class HeroUpdate(SQLModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50
    )

    age: int | None = Field(
        default=None,
        ge=0,
        le=1000
    )

    team_id: int | None = None

    secret_name: str | None = None

    power: str | None = None

    status: HeroStatus | None = None

    @field_validator("name", "status", "secret_name")
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise ValueError("cannot be null")
        return value


# =========================
# MISSION MODELS
# =========================

class MissionBase(SQLModel):
    title: str


class Mission(MissionBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    heroes: list["Hero"] = Relationship(
        back_populates="missions",
        link_model=HeroMissionLink
    )


class MissionCreate(MissionBase):
    pass


class MissionPublic(MissionBase):
    id: int
