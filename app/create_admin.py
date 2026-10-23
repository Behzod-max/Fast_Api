import argparse
from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the first administrator account."
    )
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    password = getpass("Admin password (at least 8 characters): ")
    if len(password) < 8:
        parser.error("Password must contain at least 8 characters")

    with SessionLocal() as db:
        try:
            email = str(
                TypeAdapter(EmailStr).validate_python(args.email.strip())
            ).lower()
        except ValidationError:
            parser.error("Email address is invalid")
        if db.scalar(select(User).where(User.email == email)) is not None:
            parser.error(
                "That email already exists; this command does not promote existing accounts"
            )
        db.add(User(email=email, password_hash=hash_password(password), role="admin"))
        db.commit()
    print(f"Administrator created: {email}")


if __name__ == "__main__":
    main()
