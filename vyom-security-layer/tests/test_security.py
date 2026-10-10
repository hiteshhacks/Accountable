from tests.conftest import login
from app.demo_users import DEMO_USERS

def test_missing_token_rejected(app_and_client):
    _, client = app_and_client
    assert client.get("/me").status_code == 401

def test_login_and_identity(app_and_client):
    _, client = app_and_client
    headers = login(client, "analyst-a@example.com", "correct-horse-battery-1")
    response = client.get("/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["organization_id"] == "org-a"

def test_bad_password_rejected(app_and_client):
    _, client = app_and_client
    response = client.post("/auth/token", json={"email": "analyst-a@example.com", "password": "wrong-password"})
    assert response.status_code == 401

def test_repeated_bad_passwords_are_rate_limited(app_and_client):
    _, client = app_and_client
    for _ in range(5):
        response = client.post("/auth/token", json={"email": "analyst-a@example.com", "password": "wrong-password"})
        assert response.status_code == 401
    response = client.post("/auth/token", json={"email": "analyst-a@example.com", "password": "wrong-password"})
    assert response.status_code == 429

def test_tampered_token_rejected(app_and_client):
    _, client = app_and_client
    headers = login(client, "analyst-a@example.com", "correct-horse-battery-1")
    headers["Authorization"] = headers["Authorization"] + "tampered"
    response = client.get("/me", headers=headers)
    assert response.status_code == 401

def test_auditor_cannot_create_invoice(app_and_client):
    _, client = app_and_client
    headers = login(client, "auditor-a@example.com", "correct-horse-battery-2")
    response = client.post("/invoices", headers=headers, json={"invoice_number": "INV-1", "taxable_value": 100, "description": "Test"})
    assert response.status_code == 403

def test_cross_tenant_invoice_not_disclosed(app_and_client):
    _, client = app_and_client
    headers_a = login(client, "analyst-a@example.com", "correct-horse-battery-1")
    headers_b = login(client, "analyst-b@example.com", "correct-horse-battery-4")
    created = client.post("/invoices", headers=headers_b, json={"invoice_number": "B-PRIVATE-1", "taxable_value": 1000, "description": "Org B private record"})
    assert created.status_code == 201
    invoice_id = created.json()["id"]
    assert client.get(f"/invoices/{invoice_id}", headers=headers_a).status_code == 404
    listing = client.get("/invoices", headers=headers_a)
    assert listing.status_code == 200
    assert all(row["invoice_number"] != "B-PRIVATE-1" for row in listing.json())

def test_cross_tenant_invoice_update_not_allowed(app_and_client):
    _, client = app_and_client
    headers_a = login(client, "analyst-a@example.com", "correct-horse-battery-1")
    headers_b = login(client, "analyst-b@example.com", "correct-horse-battery-4")
    created = client.post("/invoices", headers=headers_b, json={"invoice_number": "B-PRIVATE-2", "taxable_value": 1000, "description": "Org B private record"})
    assert created.status_code == 201
    invoice_id = created.json()["id"]
    response = client.patch(f"/invoices/{invoice_id}", headers=headers_a, json={"description": "tampered"})
    assert response.status_code == 404
    unchanged = client.get(f"/invoices/{invoice_id}", headers=headers_b)
    assert unchanged.json()["description"] == "Org B private record"

def test_admin_can_soft_delete_invoice(app_and_client):
    _, client = app_and_client
    analyst_headers = login(client, "analyst-a@example.com", "correct-horse-battery-1")
    admin_headers = login(client, "admin-a@example.com", "correct-horse-battery-3")
    created = client.post("/invoices", headers=analyst_headers, json={"invoice_number": "INV-DEL", "taxable_value": 100, "description": "Delete me"})
    invoice_id = created.json()["id"]
    assert client.delete(f"/invoices/{invoice_id}", headers=analyst_headers).status_code == 403
    assert client.delete(f"/invoices/{invoice_id}", headers=admin_headers).status_code == 204
    assert client.get(f"/invoices/{invoice_id}", headers=admin_headers).status_code == 404

def test_unexpected_fields_rejected(app_and_client):
    _, client = app_and_client
    headers = login(client, "analyst-a@example.com", "correct-horse-battery-1")
    response = client.post("/invoices", headers=headers, json={"invoice_number": "INV-2", "taxable_value": 100, "description": "Test", "organization_id": "org-b", "role": "admin"})
    assert response.status_code == 422

def test_control_characters_rejected(app_and_client):
    _, client = app_and_client
    headers = login(client, "analyst-a@example.com", "correct-horse-battery-1")
    response = client.post("/invoices", headers=headers, json={"invoice_number": "INV-3", "taxable_value": 100, "description": "bad\u0000text"})
    assert response.status_code == 422

def test_security_headers(app_and_client):
    _, client = app_and_client
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"

def test_audit_endpoint_admin_only(app_and_client):
    _, client = app_and_client
    headers = login(client, "analyst-a@example.com", "correct-horse-battery-1")
    assert client.get("/audit/events", headers=headers).status_code == 403

def test_audit_endpoint_returns_denials_for_authorized_viewer(app_and_client):
    _, client = app_and_client
    analyst_headers = login(client, "analyst-a@example.com", "correct-horse-battery-1")
    admin_headers = login(client, "admin-a@example.com", "correct-horse-battery-3")
    assert client.delete("/invoices/999", headers=analyst_headers).status_code == 403
    response = client.get("/audit/events", headers=admin_headers)
    assert response.status_code == 200
    assert any(event["action"] == "authorization.denied" for event in response.json())

def test_vyom_demo_users_follow_role_permissions(app_and_client):
    _, client = app_and_client
    headers_by_role = {
        account["role"]: login(client, account["email"], account["password"])
        for account in DEMO_USERS
    }

    admin_invoice = client.post("/invoices", headers=headers_by_role["admin"],
        json={"invoice_number": "ADMIN-1", "taxable_value": 100, "description": "Admin-created invoice"})
    assert admin_invoice.status_code == 201
    invoice_id = admin_invoice.json()["id"]

    assert client.get("/invoices", headers=headers_by_role["admin"]).status_code == 200
    assert client.get("/invoices", headers=headers_by_role["finance_analyst"]).status_code == 200
    assert client.get("/invoices", headers=headers_by_role["reviewer"]).status_code == 200
    assert client.get("/invoices", headers=headers_by_role["auditor"]).status_code == 200

    finance_invoice = client.post("/invoices", headers=headers_by_role["finance_analyst"],
        json={"invoice_number": "FIN-1", "taxable_value": 200, "description": "Finance-created invoice"})
    assert finance_invoice.status_code == 201
    assert client.patch(f"/invoices/{finance_invoice.json()['id']}", headers=headers_by_role["finance_analyst"],
        json={"description": "Finance updated invoice"}).status_code == 200

    assert client.post("/invoices", headers=headers_by_role["reviewer"],
        json={"invoice_number": "REV-1", "taxable_value": 300, "description": "Reviewer attempt"}).status_code == 403
    assert client.post("/invoices", headers=headers_by_role["auditor"],
        json={"invoice_number": "AUD-1", "taxable_value": 400, "description": "Auditor attempt"}).status_code == 403

    assert client.get("/audit/events", headers=headers_by_role["admin"]).status_code == 200
    assert client.get("/audit/events", headers=headers_by_role["reviewer"]).status_code == 200
    assert client.get("/audit/events", headers=headers_by_role["auditor"]).status_code == 200
    assert client.get("/audit/events", headers=headers_by_role["finance_analyst"]).status_code == 403

    assert client.delete(f"/invoices/{invoice_id}", headers=headers_by_role["finance_analyst"]).status_code == 403
    assert client.delete(f"/invoices/{invoice_id}", headers=headers_by_role["reviewer"]).status_code == 403
    assert client.delete(f"/invoices/{invoice_id}", headers=headers_by_role["auditor"]).status_code == 403
    assert client.delete(f"/invoices/{invoice_id}", headers=headers_by_role["admin"]).status_code == 204
