import importlib.util
import io
import sqlite3
import sys
from pathlib import Path

import pytest
from flask_login import login_user


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
            CREATE TABLE compliance_actions (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                property_id INTEGER NOT NULL,
                comp_type TEXT NOT NULL,
                status TEXT NOT NULL,
                resolved_at TEXT,
                resolved_by TEXT,
                snoozed_until TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(client_id, property_id, comp_type)
            );
            """
        )
        conn.executemany(
            "INSERT INTO clients (id, name, slug, is_active, deleted_at) VALUES (?, ?, ?, 1, NULL)",
            [
                (28, "Sample Agency Alpha", "sample-agency-alpha"),
                (30, "Sample Agency Beta", "sample-agency-beta"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO users
                (id, email, full_name, role, client_id, password_hash, is_active, deleted_at)
            VALUES (?, ?, ?, ?, ?, '', 1, NULL)
            """,
            [
                (1, "admin@example.test", "Platform Admin", "admin", None),
                (2, "manager@example.test", "Demo Manager", "manager", 30),
            ],
        )
        conn.executemany(
            "INSERT INTO properties (id, client_id, address, deleted_at) VALUES (?, ?, ?, NULL)",
            [
                (101, 28, "101 Example Street, Sampletown, ZX1 1AA"),
                (102, 30, "202 Demo Avenue, Mockford, ZX2 2BB"),
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
            VALUES (?, ?, ?, ?, ?, ?, ?, '', NULL, NULL, NULL, ?, ?, NULL)
            """,
            [
                (
                    1001,
                    101,
                    28,
                    1,
                    "ALPHA-GAS-001",
                    "Sample Gas Safety",
                    "verified",
                    "2026-04-01T09:00:00",
                    "2026-04-01",
                ),
                (
                    1002,
                    102,
                    30,
                    2,
                    "BETA-TENANCY-001",
                    "Sample Tenancy",
                    "verified",
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
    (clients_dir / "Sample Agency Alpha").mkdir(parents=True)
    (clients_dir / "Sample Agency Beta").mkdir(parents=True)

    db_path = tmp_path / "portal.db"
    seed_portal_db(db_path)

    monkeypatch.setenv("DATABASE_URL", str(db_path))
    monkeypatch.setenv("MORPHIQ_CLIENTS_DIR", str(clients_dir))
    monkeypatch.setenv("PORTAL_SECRET_KEY", "test-secret")

    module = load_portal_module(
        f"portal_app_test_{tmp_path.name}",
        PORTAL_DIR / "app.py",
    )
    module.app.config.update(TESTING=True)
    module.validate_csrf = lambda: True
    return module


def login_as(client, user_id: int):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_manager_get_current_client_ignores_query_param(portal_app):
    manager = portal_app.User(
        user_id=2,
        email="manager@example.test",
        full_name="Demo Manager",
        role="manager",
        client_id=30,
        is_active=True,
    )

    with portal_app.app.test_request_context("/overview?client=Sample%20Agency%20Alpha"):
        login_user(manager)
        assert portal_app.get_current_client() == "Sample Agency Beta"


def test_admin_get_current_client_persists_query_param(portal_app):
    admin = portal_app.User(
        user_id=1,
        email="admin@example.test",
        full_name="Platform Admin",
        role="admin",
        client_id=None,
        is_active=True,
    )

    with portal_app.app.test_request_context("/overview?client=Sample%20Agency%20Beta"):
        login_user(admin)
        assert portal_app.get_current_client() == "Sample Agency Beta"
        assert portal_app.session["selected_client"] == "Sample Agency Beta"


def test_manager_cannot_fetch_global_client_list(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/api/clients")

    assert response.status_code == 403


def test_admin_can_fetch_active_client_list(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 1)

    response = client.get("/api/clients")

    assert response.status_code == 200
    payload = response.get_json()
    assert [row["name"] for row in payload["clients"]] == [
        "Sample Agency Alpha",
        "Sample Agency Beta",
    ]


def test_manager_properties_are_scoped_to_assigned_client(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/api/properties?client=Sample%20Agency%20Alpha")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert [row["client_name"] for row in payload["properties"]] == ["Sample Agency Beta"]
    assert [row["property_id"] for row in payload["properties"]] == [102]


def test_admin_properties_respect_selected_client_scope(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 1)

    response = client.get("/api/properties?client=Sample%20Agency%20Alpha")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert [row["client_name"] for row in payload["properties"]] == ["Sample Agency Alpha"]
    assert [row["property_id"] for row in payload["properties"]] == [101]


def test_manager_documents_are_scoped_to_assigned_client(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/api/documents?client=Sample%20Agency%20Alpha")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert [row["client_name"] for row in payload["documents"]] == ["Sample Agency Beta"]
    assert [row["source_doc_id"] for row in payload["documents"]] == ["BETA-TENANCY-001"]


def test_admin_documents_respect_selected_client_scope(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 1)

    response = client.get("/api/documents?client=Sample%20Agency%20Alpha")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert [row["client_name"] for row in payload["documents"]] == ["Sample Agency Alpha"]
    assert [row["source_doc_id"] for row in payload["documents"]] == ["ALPHA-GAS-001"]


def test_manager_can_fetch_property_detail_for_assigned_client(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/api/properties/102")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["property"]["property_id"] == 102
    assert payload["property"]["client_name"] == "Sample Agency Beta"


def test_manager_cannot_fetch_property_detail_for_other_client(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/api/properties/101")

    assert response.status_code == 404


def test_admin_can_fetch_property_detail_across_clients(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 1)

    response = client.get("/api/properties/101")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["property"]["property_id"] == 101
    assert payload["property"]["client_name"] == "Sample Agency Alpha"


def test_manager_cannot_fetch_property_report_for_other_client(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/api/properties/101/report?format=pdf")

    assert response.status_code == 404


def test_manager_cannot_download_property_pack_for_other_client(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.post("/api/properties/101/download-pack")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Property not found"}


def test_manager_cannot_fetch_document_by_id_for_other_client(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/api/documents/by-id/1001")

    assert response.status_code == 404


def test_admin_can_fetch_document_by_id_across_clients(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 1)

    response = client.get("/api/documents/by-id/1001")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["id"] == 1001
    assert payload["client_name"] == "Sample Agency Alpha"


def test_manager_cannot_fetch_document_by_source_for_other_client(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/api/documents/ALPHA-GAS-001")

    assert response.status_code == 404


def test_manager_cannot_fetch_document_pdf_by_id_for_other_client(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/api/documents/by-id/1001/pdf")

    assert response.status_code == 404


def test_manager_cannot_fetch_document_pdf_by_source_for_other_client(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/api/documents/by-source/ALPHA-GAS-001/pdf")

    assert response.status_code == 404


def test_manager_cannot_view_settings_users(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.get("/api/settings/users")

    assert response.status_code == 403
    assert response.get_json() == {"error": "Forbidden"}


def test_admin_can_view_settings_users(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 1)

    response = client.get("/api/settings/users")

    assert response.status_code == 200
    payload = response.get_json()
    assert {row["role"] for row in payload["users"]} == {"admin", "manager"}


def test_manager_cannot_create_clients(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.post("/admin/clients", json={"name": "Should Not Work"})

    assert response.status_code == 403
    assert response.get_json() == {"error": "Forbidden"}


def test_manager_cannot_create_users(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.post(
        "/admin/users",
        json={
            "email": "blocked@example.com",
            "full_name": "Blocked User",
            "role": "manager",
            "client_id": 30,
            "password": "password123",
        },
    )

    assert response.status_code == 403
    assert response.get_json() == {"error": "Forbidden"}


def test_manager_cannot_upload_document_for_other_client_property(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.post(
        "/api/documents/upload",
        data={
            "property_id": "101",
            "document_type": "Gas Safety Certificate",
            "file": (io.BytesIO(b"%PDF-1.4 test"), "test.pdf"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Property not found"}


def test_manager_cannot_resolve_compliance_for_other_client_property(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.post(
        "/api/compliance/actions/resolve",
        json={"property_id": 101, "comp_type": "gas_safety", "notes": "try cross-client"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Property not found"}


def test_manager_cannot_snooze_compliance_for_other_client_property(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)

    response = client.post(
        "/api/compliance/actions/snooze",
        json={"property_id": 101, "comp_type": "gas_safety", "days": 7, "notes": "try cross-client"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Property not found"}


def test_manager_cannot_modify_document_config(portal_app):
    client = portal_app.app.test_client()
    login_as(client, 2)
    with client.session_transaction() as session:
        session["_csrf_token"] = "test-csrf-token"

    response = client.post(
        "/api/settings/document-config",
        json={
            "document_type": {
                "key": "fire-door-certificate",
                "label": "Fire Door Certificate",
            },
            "extraction_fields": [
                {"field_key": "door_location", "field_label": "Door Location", "is_required": True},
            ],
            "compliance_rules": [],
            "dashboard": {"show_in_dashboard": True},
        },
        headers={"X-CSRF-Token": "test-csrf-token"},
    )

    assert response.status_code == 403
    assert response.get_json() == {"error": "Forbidden"}
