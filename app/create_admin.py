"""Create an admin locally: python -m app.create_admin admin [password]."""

import argparse
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.database import engine
from app.models import Role, User, UserCreate
from app.security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an administrator account")
    parser.add_argument("username")
    parser.add_argument("password", nargs="?", help="Omit to enter it privately")
    args = parser.parse_args()
    try:
        credentials = UserCreate(
            username=args.username,
            password=args.password if args.password is not None else getpass("Password: "),
        )
    except ValidationError:
        parser.exit(1, "Username must be 3–30 characters; password at least 8 characters and at most 72 UTF-8 bytes.\n")

    with Session(engine) as session:
        user = User(
            username=credentials.username,
            hashed_password=hash_password(credentials.password),
            role=Role.admin,
        )
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            parser.exit(1, "Username already taken.\n")
    print(f"Admin '{credentials.username}' created.")


if __name__ == "__main__":
    main()
