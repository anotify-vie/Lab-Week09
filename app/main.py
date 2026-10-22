from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel

from app.database import engine
from app.routers import auth, heroes, missions, teams


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates a fresh database. Existing databases must use Alembic migrations.
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(
    title="Heroes API",
    version="0.11.0",
    description="Public reads, JWT authentication, and owner/admin permissions.",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "auth", "description": "Register, log in, and view your account."},
        {"name": "heroes", "description": "Heroes and their owners."},
        {"name": "teams", "description": "Public team reads and admin-only creation."},
        {"name": "missions", "description": "Missions and hero assignments."},
    ],
)

for router in (auth.router, heroes.router, teams.router, missions.router):
    app.include_router(router, prefix="/api/v1")
    # Keep Week 9 URLs working with exactly the same permission dependencies.
    app.include_router(router, include_in_schema=False)


@app.get("/", summary="API health")
def root():
    return {"message": "Hero API is running"}


app.mount(
    "/frontend",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "frontend", html=True),
    name="frontend",
)
