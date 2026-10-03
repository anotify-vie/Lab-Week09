from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Response
from sqlmodel import SQLModel, select

from app import models
from app.database import engine, SessionDep
from app.models import Hero, HeroCreate, HeroPublic, HeroUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return {"message": "Hero API is running"}

@app.post("/heroes", response_model=HeroPublic, status_code=201)
def create_hero(hero_in: HeroCreate, session: SessionDep):
    hero = Hero.model_validate(hero_in)
    session.add(hero)
    session.commit()
    session.refresh(hero)
    return hero

@app.get("/heroes", response_model=list[HeroPublic])
def list_heroes(
    session: SessionDep,
    offset: int = 0,
    limit: int = Query(default=10, le=100)
):
    statement = (
        select(Hero)
        .order_by(Hero.id)
        .offset(offset)
        .limit(limit)
    )
    heroes = session.exec(statement).all()

    return heroes

@app.get("/heroes/{hero_id}", response_model=HeroPublic)
def get_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if hero is None:
        raise HTTPException(
            status_code=404,
            detail="Hero not found"
        )
    return hero

@app.patch("/heroes/{hero_id}", response_model=HeroPublic)
def update_hero(
    hero_id: int,
    hero_in: HeroUpdate,
    session: SessionDep
):
    hero = session.get(Hero, hero_id)
    if hero is None:
        raise HTTPException(
            status_code=404,
            detail="Hero not found"
        )
    hero_data = hero_in.model_dump(exclude_unset=True)
    hero.sqlmodel_update(hero_data)
    session.add(hero)
    session.commit()
    session.refresh(hero)
    return hero

@app.delete("/heroes/{hero_id}", status_code=204)
def delete_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if hero is None:
        raise HTTPException(
            status_code=404,
            detail="Hero not found"
        )
    session.delete(hero)
    session.commit()
    return Response(status_code=204)