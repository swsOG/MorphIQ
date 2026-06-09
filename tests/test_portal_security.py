"""Security regression tests for the Portal (portal_new/app.py).

Covers: C-4 (weak-secret boot guard), H-1 (X-Forwarded-For spoofing + per-account
lockout), M-1 (security headers), and L-1 (fail-closed tenant scoping).
"""
import sqlite3

import pytest

from test_portal_auth import seed_portal_db, load_portal_module, PORTAL_DIR

STRONG_SECRET = "unit-test-secret-key-0123456789abcdef0123456789"


def _make_app(tmp_path, monkeypatch, extra_env=None):
    clients_dir = tmp_path / "Clients"
    (clients_dir / "Sample Agency Alpha").mkdir(parents=True)
    (clients_dir / "Sample Agency Beta").mkdir(parents=True)
    db_path = tmp_path / "portal.db"
    seed_portal_db(db_path)
    monkeypatch.setenv("DATABASE_URL", str(db_path))
    monkeypatch.setenv("MORPHIQ_CLIENTS_DIR", str(clients_dir))
    monkeypatch.setenv("PORTAL_SECRET_KEY", STRONG_SECRET)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    for k, v in (extra_env or {}).items():
        monkeypatch.setenv(k, v)
    module = load_portal_module(f"portal_sec_{tmp_path.name}", PORTAL_DIR / "app.py")
    module.app.config.update(TESTING=True)
    module.validate_csrf = lambda: True
    return module, db_path


# ── C-4: weak secret refuses to boot ─────────────────────────────────────────
def test_weak_secret_key_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTAL_SECRET_KEY", "secret")  # placeholder/weak
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "p.db"))
    with pytest.raises(RuntimeError, match="PORTAL_SECRET_KEY"):
        load_portal_module(f"portal_weak_{tmp_path.name}", PORTAL_DIR / "app.py")


# ── M-1: security headers present ────────────────────────────────────────────
def test_security_headers_present(tmp_path, monkeypatch):
    module, _ = _make_app(tmp_path, monkeypatch)
    resp = module.app.test_client().get("/login")
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("Referrer-Policy") == "same-origin"
    assert "Content-Security-Policy" in resp.headers


# ── H-1: rate-limit / lockout cannot be bypassed by spoofing X-Forwarded-For ──
def test_xff_ignored_without_trust_proxy(tmp_path, monkeypatch):
    module, _ = _make_app(tmp_path, monkeypatch)  # TRUST_PROXY unset
    client = module.app.test_client()
    codes = [
        client.post(
            "/login",
            data={"email": "manager@example.test", "password": "wrong"},
            headers={"X-Forwarded-For": f"203.0.113.{i}"},
        ).status_code
        for i in range(6)
    ]
    # Spoofed IPs are ignored -> all share one real IP key -> limiter still trips.
    assert 429 in codes


def test_per_account_lockout_survives_ip_rotation(tmp_path, monkeypatch):
    # With TRUST_PROXY on, rotating XFF bypasses the IP limiter — but the
    # per-account lockout must still stop the brute force.
    module, _ = _make_app(tmp_path, monkeypatch, extra_env={"TRUST_PROXY": "1"})
    client = module.app.test_client()
    for i in range(10):
        client.post(
            "/login",
            data={"email": "manager@example.test", "password": "wrong"},
            headers={"X-Forwarded-For": f"203.0.113.{i}"},
        )
    locked = client.post(
        "/login",
        data={"email": "manager@example.test", "password": "wrong"},
        headers={"X-Forwarded-For": "203.0.113.254"},
    )
    assert locked.status_code == 429


# ── L-1: tenant scope fails closed when a non-admin's client can't resolve ────
def test_tenant_scope_fails_closed(tmp_path, monkeypatch):
    module, db_path = _make_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "2"   # manager of client 30 (Sample Agency Beta)
        sess["_fresh"] = True

    # Baseline: manager can read their own property.
    assert client.get("/api/properties/102").status_code == 200

    # Soft-delete their client mid-session -> scope can no longer resolve.
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE clients SET deleted_at = '2026-01-01T00:00:00' WHERE id = 30")
    conn.commit()
    conn.close()

    # Fail closed: another client's (still active) property must NOT leak.
    assert client.get("/api/properties/101").status_code == 404
