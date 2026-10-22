
from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlmodel import select

from app.database import SessionDep
from app.security import AUTH_ERRORS, OWNER_ERRORS, CurrentUser, check_owner
from app.models import (
    Hero,
    HeroCreate,
    HeroPublic,
    HeroUpdate,
    Team,
)


router = APIRouter(
    prefix="/heroes",
    tags=["heroes"]
)

NOT_FOUND = {
    404: {"description": "Hero not found"}
}


# =========================
# HELPER FUNCTIONS
# =========================

def get_hero_or_404(session: SessionDep, hero_id: int) -> Hero:
    hero = session.get(Hero, hero_id)

    if hero is None:
        raise HTTPException(
            status_code=404,
            detail="Hero not found"
        )

    return hero


def check_team_exists(session: SessionDep, team_id: int | None):
    if team_id is not None and session.get(Team, team_id) is None:
        raise HTTPException(
            status_code=400,
            detail=f"Team {team_id} does not exist"
        )


# =========================
# GET ALL HEROES
# =========================

@router.get(
    "",
    response_model=list[HeroPublic],
    summary="List heroes"
)
def list_heroes(
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    min_age: int | None = Query(default=None, ge=0),
    team_id: int | None = None,
    name: str | None = None,
):
    """List heroes with pagination and optional filters."""

    statement = select(Hero).order_by(Hero.id)

    if min_age is not None:
        statement = statement.where(Hero.age >= min_age)

    if team_id is not None:
        statement = statement.where(Hero.team_id == team_id)

    if name is not None:
        statement = statement.where(
            Hero.name.ilike(f"%{name}%")
        )

    statement = statement.offset(offset).limit(limit)

    return session.exec(statement).all()


# =========================
# GET HERO BY ID
# =========================

@router.get(
    "/{hero_id}",
    response_model=HeroPublic,
    summary="Get one hero",
    responses=NOT_FOUND
)
def get_hero(hero_id: int, session: SessionDep):
    """Return a single hero by ID."""

    return get_hero_or_404(session, hero_id)


# =========================
# CREATE HERO
# =========================

@router.post(
    "",
    response_model=HeroPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a hero",
    responses={
        **AUTH_ERRORS,
        400: {"description": "Team does not exist"}
    }
)
def create_hero(hero_in: HeroCreate, session: SessionDep, user: CurrentUser):
    """Create a hero and validate the assigned team."""

    check_team_exists(session, hero_in.team_id)

    hero = Hero.model_validate(hero_in, update={"owner_id": user.id})

    session.add(hero)
    session.commit()
    session.refresh(hero)

    return hero


# =========================
# UPDATE HERO
# =========================

@router.patch(
    "/{hero_id}",
    response_model=HeroPublic,
    summary="Update a hero partially",
    responses={
        **NOT_FOUND,
        **OWNER_ERRORS,
        400: {"description": "Team does not exist"}
    }
)
def update_hero(
    hero_id: int,
    hero_in: HeroUpdate,
    session: SessionDep,
    user: CurrentUser,
):
    """Update only the fields provided by the client."""

    hero = get_hero_or_404(session, hero_id)

    check_owner(hero, user)
    hero_data = hero_in.model_dump(exclude_unset=True)

    check_team_exists(session, hero_data.get("team_id"))

    hero.sqlmodel_update(hero_data)

    session.add(hero)
    session.commit()
    session.refresh(hero)

    return hero


# =========================
# DELETE HERO
# =========================

@router.delete(
    "/{hero_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a hero",
    responses={**NOT_FOUND, **OWNER_ERRORS}
)
def delete_hero(hero_id: int, session: SessionDep, user: CurrentUser):
    """Delete a hero by ID."""

    hero = get_hero_or_404(session, hero_id)

    check_owner(hero, user)
    session.delete(hero)
    session.commit()

    return Response(status_code=204)
