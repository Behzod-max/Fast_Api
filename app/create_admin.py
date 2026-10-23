import argparse
from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import Foydalanuvchi


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Birinchi administrator hisobini xavfsiz yaratish."
    )
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    password = getpass("Administrator paroli (kamida 8 belgi): ")
    if len(password) < 8:
        parser.error("Parol kamida 8 ta belgidan iborat bo‘lishi kerak")

    with SessionLocal() as db:
        try:
            email = str(
                TypeAdapter(EmailStr).validate_python(args.email.strip())
            ).lower()
        except ValidationError:
            parser.error("Elektron pochta manzili noto‘g‘ri")
        if db.scalar(select(Foydalanuvchi).where(Foydalanuvchi.email == email)) is not None:
            parser.error(
                "Bu elektron pochta allaqachon mavjud; buyruq mavjud hisobni administratorga ko‘tarmaydi"
            )
        db.add(Foydalanuvchi(email=email, password_hash=hash_password(password), role="admin"))
        db.commit()
    print(f"Administrator yaratildi: {email}")


if __name__ == "__main__":
    main()
