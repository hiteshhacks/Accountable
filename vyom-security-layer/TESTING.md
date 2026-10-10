# Testing VYOM Security Layer

Run these commands from this folder:

```powershell
cd C:\Users\DELL\Downloads\IIITN\vyom-security-layer
C:\Users\DELL\Downloads\IIITN\Accountable_security_layer\venv\Scripts\python.exe -m pip install -r requirements.txt
C:\Users\DELL\Downloads\IIITN\Accountable_security_layer\venv\Scripts\python.exe -m pytest
```

The application package is in `app`, and tests are in `tests`. The `pytest.ini`
file points pytest to that package so imports work from the project root. It
also disables pytest's cache provider, and the test fixture uses `.test_runs`
for SQLite databases instead of pytest's `tmp_path`. This avoids Windows temp
folder and pytest cache permission errors.

To run the API manually:

```powershell
cd C:\Users\DELL\Downloads\IIITN\vyom-security-layer
$env:VYOM_JWT_SECRET="replace-this-with-a-long-random-secret-at-least-32-bytes"
C:\Users\DELL\Downloads\IIITN\Accountable_security_layer\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs`.

Security endpoints available in `/docs`:

- `POST /uploads/validate`
- `POST /llm/validate-classification`
- `POST /gst/evaluate`
- `POST /pipeline/validate`
- `GET /audit/events`

## Demo role users

In a second PowerShell window, seed the local demo users:

```powershell
cd C:\Users\DELL\Downloads\IIITN\vyom-security-layer
$env:VYOM_JWT_SECRET="replace-this-with-a-long-random-secret-at-least-32-bytes"
C:\Users\DELL\Downloads\IIITN\Accountable_security_layer\venv\Scripts\python.exe -m scripts.seed_demo_users
```

Use these accounts in `/docs` with `POST /auth/token`:

| Email | Password | Role |
|---|---|---|
| `admin@vyom.in` | `admin_vyom` | `admin` |
| `finance_analyst@vyom.in` | `finance_analyst_vyom` | `finance_analyst` |
| `reviewer@vyom.in` | `reviewer_vyom` | `reviewer` |
| `auditor@vyom.in` | `auditor_vyom` | `auditor` |

These are local demo credentials only. Do not use them for production.
