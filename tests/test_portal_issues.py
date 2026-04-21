import importlib.util
import sqlite3
import sys
import types
from pathlib import Path

import pytest


PROJECT_ROOT = Path(r"C:\Users\user\Projects\MorphIQ\Product")
PORTAL_DIR = PROJECT_ROOT / "portal_new"


def load_portal_module(module_name: str, module_path: Path):
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    if str(PORTAL_DIR) not in sys.path:
        sys.path.insert(0, str(PORTAL_DIR))
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_portal_db(db_path: Path):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                deleted_at TEXT
            );
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                client_id INTEGER,
                password_hash TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                deleted_at TEXT,
                last_login TEXT
            );
            CREATE TABLE properties (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                address TEXT NOT NULL,
                deleted_at TEXT
            );
            CREATE TABLE document_types (
                id INTEGER PRIMARY KEY,
                key TEXT NOT NULL,
                label TEXT NOT NULL
            );
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                property_id INTEGER NOT NULL,
                client_id INTEGER NOT NULL,
                document_type_id INTEGER,
                source_doc_id TEXT,
                doc_name TEXT NOT NULL,
                status TEXT,
                pdf_path TEXT,
                quality_score REAL,
                reviewed_by TEXT,
                reviewed_at TEXT,
                scanned_at TEXT,
                batch_date TEXT,
                deleted_at TEXT
            );
            CREATE TABLE document_fields (
                id INTEGER PRIMARY KEY,
                document_id INTEGER NOT NULL,
                field_key TEXT NOT NULL,
                field_label TEXT,
                field_value TEXT,
                deleted_at TEXT
            );
            """
        )
        conn.executemany(
            "INSERT INTO clients (id, name, slug, is_active, deleted_at) VALUES (?, ?, ?, 1, NULL)",
            [
                (28, "Harlow & Essex Lettings", "harlow-essex-lettings"),
                (30, "Epping Lettings", "epping-lettings"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO users
                (id, email, full_name, role, client_id, password_hash, is_active, deleted_at)
            VALUES (?, ?, ?, ?, ?, '', 1, NULL)
            """,
            [
                (1, "filip@morphiq.co.uk", "Filip", "admin", None),
                (2, "demo@epping.co.uk", "Epping Manager", "manager", 30),
                (3, "demo@harlow.co.uk", "Harlow Manager", "manager", 28),
            ],
        )
        conn.executemany(
            "INSERT INTO properties (id, client_id, address, deleted_at) VALUES (?, ?, ?, NULL)",
            [
                (101, 28, "22 Ferndale Road, Harlow, CM17 0HL"),
                (102, 30, "8 Birchwood Lane, Epping, CM16 4AA"),
            ],
        )
        conn.executemany(
            "INSERT INTO document_types (id, key, label) VALUES (?, ?, ?)",
            [
                (1, "gas-safety-certificate", "Gas Safety Certificate"),
                (2, "tenancy-agreement", "Tenancy Agreement"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO documents
                (id, property_id, client_id, document_type_id, source_doc_id, doc_name, status,
                 pdf_path, quality_score, reviewed_by, reviewed_at, scanned_at, batch_date, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, '', NULL, ?, ?, ?, ?, NULL)
            """,
            [
                (
                    1001,
                    101,
                    28,
                    1,
                    "HARLOW-GAS-001",
                    "Harlow Gas Safety",
                    "verified",
                    "Filip",
                    "2026-04-01T09:30:00",
                    "2026-04-01T09:00:00",
                    "2026-04-01",
                ),
                (
                    1002,
                    102,
                    30,
                    2,
                    "EPPING-TENANCY-001",
                    "Epping Tenancy",
                    "verified",
                    "Filip",
                    "2026-04-02T09:30:00",
                    "2026-04-02T09:00:00",
                    "2026-04-02",
                ),
            ],
        )
        conn.executemany(
            """
            INSERT INTO document_fields
                (id, document_id, field_key, field_label, field_value, deleted_at)
            VALUES (?, ?, ?, ?, ?, NULL)
            """,
            [
                (1, 1001, "expiry_date", "Expiry Date", "2027-04-01"),
                (2, 1002, "tenant_full_name", "Tenant Full Name", "Alex Tenant"),
            ],
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def portal_app(tmp_path, monkeypatch):
    clients_dir = tmp_path / "Clients"
    (clients_dir / "Harlow & Essex Lettings" / "Batches" / "2026-04-01" / "HARLOW-GAS-001").mkdir(parents=True)
    (clients_dir / "Epping Lettings" / "Batches" / "2026-04-02" / "EPPING-TENANCY-001").mkdir(parents=True)

    (clients_dir / "Harlow & Essex Lettings" / "Batches" / "2026-04-01" / "HARLOW-GAS-001" / "review.json").write_text(
        '{"status":"Verified","review":{"reviewed_by":"Filip","reviewed_at":"2026-04-01T09:30:00"}}\n',
        encoding="utf-8",
    )
    (clients_dir / "Epping Lettings" / "Batches" / "2026-04-02" / "EPPING-TENANCY-001" / "review.json").write_text(
        '{"status":"Verified","review":{"reviewed_by":"Filip","reviewed_at":"2026-04-02T09:30:00"}}\n',
        encoding="utf-8",
    )

    db_path = tmp_path / "portal.db"
    seed_portal_db(db_path)

    monkeypatch.setenv("DATABASE_URL", str(db_path))
    monkeypatch.setenv("MORPHIQ_CLIENTS_DIR", str(clients_dir))
    monkeypatch.setenv("PORTAL_SECRET_KEY", "test-secret")

    fake_sync = types.ModuleType("sync_to_portal")

    def sync_single_doc(client_name: str, source_doc_id: str):
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                UPDATE documents
                SET status = 'verified',
                    reviewed_by = 'Filip',
                    reviewed_at = '2026-05-01T12:30:00'
                WHERE source_doc_id = ?
                """,
                (source_doc_id,),
            )
            conn.commit()
        finally:
            conn.close()

    fake_sync.sync_single_doc = sync_single_doc
    monkeypatch.setitem(sys.modules, "sync_to_portal", fake_sync)

    module = load_portal_module(
        f"portal_issues_app_{tmp_path.name}",
        PORTAL_DIR / "app.py",
    )
    module.app.config.update(TESTING=True)
    module._test_db_path = db_path
    return module


def login_as(client, user_id: int):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_manager_can_report_issue_for_own_document_and_document_shows_under_review(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.post(
        "/api/documents/by-id/1002/issues",
        json={"reason_code": "incorrect_field", "note": "Tenant name is wrong"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["issue"]["status"] == "reported"
    assert payload["issue"]["target_queue"] == "review_queue"
    assert payload["issue"]["reason_code"] == "incorrect_field"

    detail = client.get("/api/documents/by-id/1002")
    assert detail.status_code == 200
    detail_payload = detail.get_json()
    assert detail_payload["current_delivery_status"] == "reported_under_review"
    assert detail_payload["issue_summary"]["open_issue_id"] == payload["issue"]["id"]

    issue_detail = client.get(f"/api/issues/{payload['issue']['id']}")
    assert issue_detail.status_code == 200
    issue_payload = issue_detail.get_json()
    assert len(issue_payload["versions"]) == 1
    assert issue_payload["versions"][0]["kind"] == "reported_snapshot"


def test_duplicate_open_issue_returns_existing_ticket(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    first = client.post(
        "/api/documents/by-id/1002/issues",
        json={"reason_code": "incorrect_field", "note": "First note"},
    )
    second = client.post(
        "/api/documents/by-id/1002/issues",
        json={"reason_code": "incorrect_field", "note": "Second note"},
    )

    assert first.status_code == 201
    assert second.status_code == 200
    second_payload = second.get_json()
    assert second_payload["created"] is False
    assert second_payload["issue"]["id"] == first.get_json()["issue"]["id"]


def test_manager_cannot_report_issue_for_other_client_document(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.post(
        "/api/documents/by-id/1001/issues",
        json={"reason_code": "image_quality", "note": "Wrong client"},
    )

    assert response.status_code == 404


def test_manager_cannot_view_other_clients_issue(portal_app):
    harlow_client = portal_app.app.test_client()
    login_as(harlow_client, 3)
    created = harlow_client.post(
        "/api/documents/by-id/1001/issues",
        json={"reason_code": "image_quality", "note": "Needs rescan"},
    )
    issue_id = created.get_json()["issue"]["id"]

    epping_client = portal_app.app.test_client()
    login_as(epping_client, 2)
    response = epping_client.get(f"/api/issues/{issue_id}")

    assert response.status_code == 404


def test_manager_can_use_general_support_thread(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    create = client.post(
        "/api/support/messages",
        json={"body": "Hi, one of my documents still looks odd."},
    )

    assert create.status_code == 201
    payload = create.get_json()
    assert payload["message"]["body"] == "Hi, one of my documents still looks odd."
    assert payload["message"]["thread_type"] == "general_support"

    listing = client.get("/api/support/messages")
    assert listing.status_code == 200
    messages = listing.get_json()["messages"]
    assert len(messages) == 1
    assert messages[0]["body"] == "Hi, one of my documents still looks odd."


def test_admin_can_open_dedicated_issues_workspace(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 1)

    response = client.get("/issues")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Issues workspace" in body
    assert "Rework queue" in body
    assert "Open issues" in body
    assert "Awaiting re-verification" in body
    assert ">Issues<" in body


def test_manager_cannot_open_admin_issues_workspace(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/issues")

    assert response.status_code == 403


def test_client_portal_surfaces_show_issue_and_support_entry_points(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    document_page = client.get("/document/by-id/1002")
    settings_page = client.get("/settings")

    assert document_page.status_code == 200
    assert settings_page.status_code == 200

    document_html = document_page.get_data(as_text=True)
    settings_html = settings_page.get_data(as_text=True)

    assert "Delivery assurance" in document_html
    assert "What happens next" in document_html
    assert "Report a problem" in document_html
    assert "Open support chat" in document_html
    assert "Issue timeline" in document_html
    assert "Support and delivery follow-up" in settings_html
    assert "Support chat" in settings_html
    assert "Best for" in settings_html


def test_issue_resolves_only_after_document_is_reverified(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    created = client.post(
        "/api/documents/by-id/1002/issues",
        json={"reason_code": "incorrect_field", "note": "Tenant name is wrong"},
    )
    assert created.status_code == 201
    issue_id = created.get_json()["issue"]["id"]

    conn = sqlite3.connect(portal_app._test_db_path)
    try:
        conn.execute(
            """
            UPDATE documents
            SET status = 'needs_review',
                reviewed_at = NULL
            WHERE id = 1002
            """
        )
        conn.commit()
    finally:
        conn.close()

    verify = client.post("/api/documents/by-id/1002/verify")
    assert verify.status_code == 200

    detail = client.get("/api/documents/by-id/1002")
    assert detail.status_code == 200
    detail_payload = detail.get_json()
    assert detail_payload["current_delivery_status"] == "corrected_verified"

    issue_detail = client.get(f"/api/issues/{issue_id}")
    assert issue_detail.status_code == 200
    issue_payload = issue_detail.get_json()
    assert issue_payload["issue"]["status"] == "resolved"
    assert issue_payload["issue"]["corrected_document_version_id"] is not None
    assert [version["kind"] for version in issue_payload["versions"]] == [
        "reported_snapshot",
        "corrected_snapshot",
    ]


def test_admin_can_list_and_assign_reported_issues(portal_app):
    manager_client = portal_app.app.test_client()
    login_as(manager_client, 2)
    created = manager_client.post(
        "/api/documents/by-id/1002/issues",
        json={"reason_code": "incorrect_field", "note": "Tenant name is wrong"},
    )
    issue_id = created.get_json()["issue"]["id"]

    admin_client = portal_app.app.test_client()
    login_as(admin_client, 1)

    listing = admin_client.get("/api/issues?queue=review_queue")
    assert listing.status_code == 200
    issues = listing.get_json()["issues"]
    assert [issue["id"] for issue in issues] == [issue_id]

    assign = admin_client.post(
        f"/api/issues/{issue_id}/assign",
        json={"assigned_user_id": 1},
    )
    assert assign.status_code == 200
    assign_payload = assign.get_json()
    assert assign_payload["issue"]["assigned_user_id"] == 1
    assert assign_payload["issue"]["assigned_user_name"] == "Filip"


def test_manager_cannot_assign_issue(portal_app):
    manager_client = portal_app.app.test_client()
    login_as(manager_client, 2)
    created = manager_client.post(
        "/api/documents/by-id/1002/issues",
        json={"reason_code": "incorrect_field", "note": "Tenant name is wrong"},
    )
    issue_id = created.get_json()["issue"]["id"]

    response = manager_client.post(
        f"/api/issues/{issue_id}/assign",
        json={"assigned_user_id": 1},
    )

    assert response.status_code == 403
    assert response.get_json() == {"error": "Forbidden"}
