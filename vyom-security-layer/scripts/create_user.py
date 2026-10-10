import argparse
from sqlalchemy import select
from app.config import Settings
from app.database import Base, make_engine, make_session_factory
from app.models import User
from app.security import ALLOWED_ROLES, hash_password

def main():
    parser = argparse.ArgumentParser(description="Create a user for the local VYOM security prototype")
    parser.add_argument("--email", required=True)
    parser.add_argument("--organization", required=True)
    parser.add_argument("--role", required=True, choices=sorted(ALLOWED_ROLES))
    parser.add_argument("--password", required=True, help="Use a temporary local password; shell history may expose arguments")
    args = parser.parse_args()
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    db = make_session_factory(engine)()
    try:
        email = args.email.strip().lower()
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("A user with that email already exists")
        user = User(email=email, organization_id=args.organization.strip(), role=args.role,
                    password_hash=hash_password(args.password))
        db.add(user)
        db.commit()
        print(f"Created user id={user.id}, email={user.email}, organization={user.organization_id}, role={user.role}")
    finally:
        db.close()
        engine.dispose()

if __name__ == "__main__":
    main()
