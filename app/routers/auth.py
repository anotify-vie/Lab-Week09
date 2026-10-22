from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.database import SessionDep
from app.models import Token, User, UserCreate, UserPublic
from app.security import (
    AUTH_ERRORS,
    CurrentUser,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(tags=["auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=201,
    summary="Register an account",
    responses={409: {"description": "Username already taken"}},
)
def register(user_in: UserCreate, session: SessionDep):
    """Create a regular user; the server chooses the role and stores only a hash."""
    user = User(
        username=user_in.username,
        hashed_password=hash_password(user_in.password),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Username already taken") from None
    session.refresh(user)
    return user


@router.post(
    "/token",
    response_model=Token,
    summary="Log in with a form and receive a Bearer token",
    responses={401: {"description": "Incorrect username or password"}},
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep
):
    user = session.exec(select(User).where(User.username == form.username)).first()
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(user.id)))


@router.get(
    "/me", response_model=UserPublic, summary="Get your account", responses=AUTH_ERRORS
)
def read_me(user: CurrentUser):
    return user
