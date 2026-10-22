import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.database import SessionDep
from app.models import Hero, Role, User

load_dotenv()
SECRET_KEY = os.environ["SECRET_KEY"]
if not SECRET_KEY.strip():
    raise RuntimeError("SECRET_KEY must not be empty")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
    raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

AUTH_ERRORS = {401: {"description": "Missing, invalid, or expired Bearer token"}}
OWNER_ERRORS = {**AUTH_ERRORS, 403: {"description": "Owner or admin required"}}
ADMIN_ERRORS = {**AUTH_ERRORS, 403: {"description": "Admins only"}}


def hash_password(plain: str) -> str:
    if len(plain.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    # bcrypt 4.0.1 otherwise silently truncates passwords after 72 bytes.
    if len(plain.encode("utf-8")) > 72:
        return False
    try:
        return pwd_context.verify(plain, hashed)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": subject, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep
) -> User:
    credentials_error = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
        user_id = int(payload["sub"])
        if not 0 < user_id <= 2**63 - 1:
            raise ValueError("Invalid user ID")
    except (JWTError, KeyError, ValueError, TypeError, OverflowError):
        raise credentials_error from None

    user = session.get(User, user_id)
    if user is None:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Admins only")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def check_owner(hero: Hero, user: User) -> None:
    if hero.owner_id != user.id and user.role != Role.admin:
        raise HTTPException(status_code=403, detail="You can only modify your own heroes")
