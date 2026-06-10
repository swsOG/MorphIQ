"""Security regression tests for the ScanStation API (server.py).

Covers the hardening for findings C-1 (loopback-only Host guard) and C-2/C-3
(path-segment sanitisation that blocks path traversal / arbitrary file access).
"""
import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORTAL_DIR = PROJECT_ROOT / "portal_new"


def _load_server(base_dir: Path, monkeypatch):
    for p in (str(PROJECT_ROOT), str(PORTAL_DIR)):
        if p not in sys.path:
            sys.path.insert(0, p)
    monkeypatch.setenv("MORPHIQ_BASE", str(base_dir))
    spec = importlib.util.spec_from_file_location(
        f"scanstation_server_{base_dir.name}", PROJECT_ROOT / "server.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def scan(tmp_path, monkeypatch):
    # BASE holds the "loot" an attacker would try to read via traversal.
    (tmp_path / "portal.db").write_bytes(b"SQLite format 3\x00" + b"secrethash" * 50)
    (tmp_path / ".env").write_text("PORTAL_SECRET_KEY=super-secret\n", encoding="utf-8")
    (tmp_path / "Clients" / "Victim" / "raw").mkdir(parents=True)
    module = _load_server(tmp_path, monkeypatch)
    return module.app.test_client()


def test_health_and_clients_work_normally(scan):
    assert scan.get("/health").status_code == 200
    assert scan.get("/clients").status_code == 200


def test_path_traversal_to_portal_db_is_blocked(scan):
    resp = scan.get("/raw-file/Victim/..%5c..%5c..%5cportal.db")
    assert resp.status_code == 400
    assert b"SQLite format 3" not in resp.data


def test_path_traversal_to_env_is_blocked(scan):
    resp = scan.get("/raw-file/Victim/..%5c..%5c..%5c.env")
    assert resp.status_code == 400
    assert b"PORTAL_SECRET_KEY" not in resp.data


def test_malformed_client_name_is_rejected(scan):
    assert scan.get("/docs/..%5c..%5cetc").status_code == 400


def test_non_loopback_host_is_rejected(scan):
    resp = scan.get("/clients", headers={"Host": "evil.example.com"})
    assert resp.status_code == 403


def test_loopback_host_is_allowed(scan):
    assert scan.get("/clients", headers={"Host": "127.0.0.1:8765"}).status_code == 200
