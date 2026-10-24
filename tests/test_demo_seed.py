"""A fresh install must work: core schema + synthetic demo data + the portal on top."""
import sqlite3
import sys

from test_portal_auth import PORTAL_DIR, PROJECT_ROOT, load_portal_module

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import init_portal_db  # noqa: E402
import seed_demo_data  # noqa: E402

STRONG_SECRET = "unit-test-secret-key-0123456789abcdef0123456789"


def test_init_portal_db_is_idempotent(tmp_path):
    db = tmp_path / "portal.db"
    init_portal_db.init_db(db)
    init_portal_db.init_db(db)  # second run must not fail or duplicate anything
    tables = {r[0] for r in sqlite3.connect(db).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"clients", "users", "properties", "documents", "document_fields", "compliance_records"} <= tables


def test_demo_seed_serves_a_working_portal(tmp_path, monkeypatch):
    result = seed_demo_data.seed(tmp_path / "demo", password="demo-password-for-tests")
    assert result["properties"] == 10
    assert result["documents"] > 30

    monkeypatch.setenv("DATABASE_URL", str(result["db"]))
    monkeypatch.setenv("MORPHIQ_CLIENTS_DIR", str(result["clients"]))
    monkeypatch.setenv("PORTAL_SECRET_KEY", STRONG_SECRET)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    module = load_portal_module(f"portal_demo_{tmp_path.name}", PORTAL_DIR / "app.py")
    module.app.config.update(TESTING=True)
    module.validate_csrf = lambda: True

    client = module.app.test_client()
    login = client.post(
        "/login",
        data={"email": "manager@morphiq-demo.test", "password": "demo-password-for-tests"},
    )
    assert login.status_code in (302, 303)

    for page in ("/overview", "/properties", "/compliance", "/documents", "/reports"):
        assert client.get(page).status_code == 200, page

    compliance = client.get("/api/compliance")
    assert compliance.status_code == 200

    report = client.get("/api/compliance/report?format=pdf")
    assert report.status_code == 200
    assert report.data[:4] == b"%PDF"
