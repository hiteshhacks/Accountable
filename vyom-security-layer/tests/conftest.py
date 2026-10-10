import os
os.environ.setdefault("VYOM_JWT_SECRET", "test-secret-for-module-import-only-" + "x" * 20)
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.demo_users import DEMO_ORGANIZATION_ID, DEMO_USERS
from app.main import create_app
from app.models import User
from app.security import hash_password, password_hash

@pytest.fixture()
def app_and_client():
    test_data_dir = Path(__file__).resolve().parents[1] / ".test_runs"
    test_data_dir.mkdir(exist_ok=True)
    db_path = test_data_dir / f"{uuid4().hex}.db"
    settings = Settings(database_url=f"sqlite:///{db_path}",
        jwt_secret="test-secret-not-for-production-" + "x" * 20,
        jwt_issuer="test-issuer", jwt_audience="test-audience", access_token_minutes=15, debug=False)
    app = create_app(settings)
    with TestClient(app) as client:
        db = app.state.session_factory()
        users = [
            User(email="analyst-a@example.com", password_hash=hash_password("correct-horse-battery-1"), organization_id="org-a", role="finance_analyst"),
            User(email="auditor-a@example.com", password_hash=hash_password("correct-horse-battery-2"), organization_id="org-a", role="auditor"),
            User(email="admin-a@example.com", password_hash=hash_password("correct-horse-battery-3"), organization_id="org-a", role="admin"),
            User(email="analyst-b@example.com", password_hash=hash_password("correct-horse-battery-4"), organization_id="org-b", role="finance_analyst"),
        ]
        users.extend(
            User(email=account["email"], password_hash=password_hash.hash(account["password"]),
                 organization_id=DEMO_ORGANIZATION_ID, role=account["role"])
            for account in DEMO_USERS
        )
        db.add_all(users)
        db.commit()
        db.close()
        yield app, client
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass

def login(client, email, password):
    response = client.post("/auth/token", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}
