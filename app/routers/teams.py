
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.database import SessionDep
from app.security import ADMIN_ERRORS, AdminUser
from app.models import (
    Team,
    TeamCreate,
    TeamPublic,
    HeroPublic
)


router = APIRouter(
    prefix="/teams",
    tags=["teams"]
)


# =========================
# CREATE TEAM
# =========================

@router.post(
    "",
    response_model=TeamPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a team",
    responses={
        **ADMIN_ERRORS,
        409: {"description": "Team name already exists"}
    }
)
def create_team(team_in: TeamCreate, session: SessionDep, admin: AdminUser):
    """Create a new team. Team names must be unique."""

    team = Team.model_validate(team_in)

    session.add(team)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Team name already exists"
        )

    session.refresh(team)

    return team


# =========================
# GET ALL TEAMS
# =========================

@router.get(
    "",
    response_model=list[TeamPublic],
    summary="List teams"
)
def list_teams(session: SessionDep):
    """Return all teams ordered by ID."""

    statement = select(Team).order_by(Team.id)

    teams = session.exec(statement).all()

    return teams


# =========================
# GET HEROES OF A TEAM
# =========================

@router.get(
    "/{team_id}/heroes",
    response_model=list[HeroPublic],
    summary="List the heroes of a team",
    responses={
        404: {"description": "Team not found"}
    }
)
def get_team_heroes(team_id: int, session: SessionDep):
    """Return all heroes belonging to a specific team."""

    team = session.get(Team, team_id)

    if team is None:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    return team.heroes
