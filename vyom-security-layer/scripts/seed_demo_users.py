from sqlalchemy import select
from app.config import Settings
from app.database import Base, make_engine, make_session_factory
from app.demo_users import DEMO_ORGANIZATION_ID, DEMO_USERS
from app.models import User
from app.security import password_hash


def main():
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    db = make_session_factory(engine)()
    try:
        for account in DEMO_USERS:
            email = account["email"].lower()
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(email=email, organization_id=DEMO_ORGANIZATION_ID, role=account["role"],
                            password_hash=password_hash.hash(account["password"]))
                db.add(user)
                action = "created"
            else:
                user.organization_id = DEMO_ORGANIZATION_ID
                user.role = account["role"]
                user.password_hash = password_hash.hash(account["password"])
                user.is_active = True
                action = "updated"
            db.commit()
            print(f"{action}: email={email}, password={account['password']}, role={account['role']}, organization={DEMO_ORGANIZATION_ID}")
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
