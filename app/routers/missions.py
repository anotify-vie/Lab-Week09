
from fastapi import APIRouter, HTTPException, Response, status

from app.database import SessionDep
from app.security import AUTH_ERRORS, OWNER_ERRORS, CurrentUser, check_owner
from app.models import (
    Hero,
    Mission,
    MissionCreate,
    MissionPublic
)


router = APIRouter(
    tags=["missions"]
)


# =========================
# CREATE MISSION
# =========================

@router.post(
    "/missions",
    response_model=MissionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a mission",
    responses=AUTH_ERRORS,
)
def create_mission(
    mission_in: MissionCreate,
    session: SessionDep,
    user: CurrentUser,
):
    """Create a new mission."""

    mission = Mission.model_validate(mission_in)

    session.add(mission)
    session.commit()
    session.refresh(mission)

    return mission


# =========================
# ASSIGN HERO TO MISSION
# =========================

@router.post(
    "/heroes/{hero_id}/missions/{mission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Assign a hero to a mission",
    responses={
        **OWNER_ERRORS,
        404: {"description": "Hero or Mission not found"}
    }
)
def assign_hero_to_mission(
    hero_id: int,
    mission_id: int,
    session: SessionDep,
    user: CurrentUser,
):
    """Assign an existing hero to an existing mission."""

    hero = session.get(Hero, hero_id)

    if hero is None:
        raise HTTPException(
            status_code=404,
            detail="Hero not found"
        )

    mission = session.get(Mission, mission_id)

    if mission is None:
        raise HTTPException(
            status_code=404,
            detail="Mission not found"
        )

    check_owner(hero, user)

    if mission not in hero.missions:
        hero.missions.append(mission)

        session.add(hero)
        session.commit()

    return Response(status_code=204)


# =========================
# GET HERO MISSIONS
# =========================

@router.get(
    "/heroes/{hero_id}/missions",
    response_model=list[MissionPublic],
    summary="Get missions of a hero",
    responses={
        404: {"description": "Hero not found"}
    }
)
def get_hero_missions(
    hero_id: int,
    session: SessionDep
):
    """Return all missions assigned to a hero."""

    hero = session.get(Hero, hero_id)

    if hero is None:
        raise HTTPException(
            status_code=404,
            detail="Hero not found"
        )

    return hero.missions
