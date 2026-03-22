"""
MorphIQ Portal — Document Archive Viewer
Flask app serving the search-first portal UI + JSON API.
Connects to SQLite at DATABASE_URL (default: portal.db in project root).
"""

import io
import os
import re
from pathlib import Path
from typing import Optional
import sqlite3
import zipfile
import json
import anthropic
from datetime import datetime, date, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from urllib.parse import quote
from flask import Flask, render_template, jsonify, request, send_file, abort
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import check_password_hash

# Import compliance engine in a way that works both when this file is executed
# as a script (python portal_new/app.py) and when imported as a package
# (python -m portal_new.app).
try:
    from . import compliance_engine  # type: ignore[import]
except ImportError:
    import compliance_engine  # type: ignore[no-redef]

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL", os.path.join(BASE_DIR, "..", "portal.db"))


def get_clients_dir() -> str:
    """
    Absolute path to the pipeline Clients/ folder (same convention as sync_to_portal.py).

    Priority:
      1. MORPHIQ_CLIENTS_DIR — path to Clients (or set it to .../Clients)
      2. BASE_DIR/Clients — e.g. C:\\ScanSystem_v2 when BASE_DIR is set
      3. dirname(portal.db)/Clients — repo/project root when DATABASE_URL is default
    """
    explicit = (os.environ.get("MORPHIQ_CLIENTS_DIR") or "").strip()
    if explicit:
        return explicit
    base = (os.environ.get("BASE_DIR") or "").strip()
    if base:
        return os.path.join(base, "Clients")
    return os.path.join(os.path.dirname(os.path.abspath(DATABASE_URL)), "Clients")


def _find_doc_folder_portal(client_name: str, doc_id: str) -> Optional[Path]:
    """Find the DOC-XXXXX folder under Clients/<client>/Batches/ (same layout as ScanStation server)."""
    if not (client_name or "").strip() or not (doc_id or "").strip():
        return None
    batches_path = Path(get_clients_dir()) / client_name.strip() / "Batches"
    if not batches_path.exists():
        return None
    for date_folder in batches_path.iterdir():
        if not date_folder.is_dir():
            continue
        doc_folder = date_folder / doc_id
        if doc_folder.is_dir() and (doc_folder / "review.json").exists():
            return doc_folder
    return None


def _first_pdf_in_folder(folder: Path) -> Optional[Path]:
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() == ".pdf":
            return f
    return None


def _resolve_pdf_path_for_document(doc: dict) -> Optional[str]:
    """Absolute path to the PDF on disk, or None."""
    raw = (doc.get("pdf_path") or "").strip()
    if raw:
        candidates = [raw, os.path.join(BASE_DIR, "..", raw)]
        for p in candidates:
            if os.path.isfile(p):
                return os.path.abspath(p)
    cname = (doc.get("client_name") or "").strip()
    sid = (doc.get("source_doc_id") or "").strip()
    if cname and sid:
        folder = _find_doc_folder_portal(cname, sid)
        if folder:
            pdf = _first_pdf_in_folder(folder)
            if pdf and pdf.is_file():
                return str(pdf.resolve())
    return None


app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.secret_key = os.environ.get("PORTAL_SECRET_KEY", "morphiq-dev-secret-change-in-prod")


# ── Auth / Flask-Login setup ─────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(
        self,
        user_id: int,
        email: str,
        full_name: str,
        role: str,
        client_id: int | None,
        is_active: bool = True,
    ):
        self.id = str(user_id)
        self.email = email
        self.full_name = full_name
        self.role = role
        self.client_id = client_id
        self._is_active = bool(is_active)

    def get_id(self) -> str:
        return self.id

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return self._is_active


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    if not user_id:
        return None
    conn = get_db()
    try:
        cur = conn.execute(
            """
            SELECT id, email, full_name, role, client_id, is_active
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return User(
            user_id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            role=row["role"],
            client_id=row["client_id"],
            is_active=row["is_active"],
        )
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def get_current_client() -> str | None:
    """
    Resolve the active client name for the current request.

    - Admin users (role=admin): honour ?client= query parameter (optional).
    - Manager users (role=manager): always use their assigned client_id, ignore ?client=.
    """
    if not current_user.is_authenticated:
        return None

    role = getattr(current_user, "role", None)
    client_id = getattr(current_user, "client_id", None)

    if role == "manager" and client_id:
        conn = get_db()
        try:
            cur = conn.execute(
                "SELECT name FROM clients WHERE id = ?",
                (client_id,),
            )
            row = cur.fetchone()
            return (row["name"] if row else None) or None
        finally:
            conn.close()

    # Admin (or anything else): fall back to query parameter.
    client = request.args.get("client", "").strip()
    return client or None


def _norm_client_name(name: str | None) -> str:
    """Case- and whitespace-insensitive client name comparison (portal vs DB)."""
    return " ".join((name or "").split()).casefold()


def scanstation_pdf_url(client_name: str | None, source_doc_id: str | None) -> str | None:
    """URL to open the document PDF via ScanStation API (same as property detail `pdf_url`)."""
    c = (client_name or "").strip()
    s = (source_doc_id or "").strip()
    if not c or not s:
        return None
    # page-width: scale to viewer width (minimizes side grey on wide panels). page-fit shrinks portrait pages.
    # toolbar=0/navpanes=0 hide Chromium PDF chrome in embedded iframes.
    return f"http://127.0.0.1:8765/pdf/{quote(c)}/{quote(s)}#toolbar=0&navpanes=0&page=1&zoom=page-width"


# ── Database helpers ─────────────────────────────────────────────────────────
def get_db():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn


def query_db(sql, args=(), one=False):
    """Execute a query and return results as list of dicts."""
    conn = get_db()
    try:
        cur = conn.execute(sql, args)
        rows = [dict(row) for row in cur.fetchall()]
        return rows[0] if one and rows else (None if one else rows)
    finally:
        conn.close()


def cleanup_stale_clients():
    """Remove clients from portal.db whose Clients/ folder no longer exists on disk."""
    clients_dir = get_clients_dir()
    if not os.path.isdir(clients_dir):
        return

    # Only subdirectories count as client folders (matches folder names in DB).
    disk_clients = {
        name
        for name in os.listdir(clients_dir)
        if os.path.isdir(os.path.join(clients_dir, name))
    }
    # Never wipe the DB because the wrong path was empty (e.g. legacy default C:\\ScanSystem_v2\\Clients).
    if not disk_clients:
        print(
            "cleanup_stale_clients: Clients folder has no subfolders; "
            "skipping stale removal (see MORPHIQ_CLIENTS_DIR / DATABASE_URL)."
        )
        return

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM clients")
        rows = cur.fetchall()

        for row in rows:
            client_id = row["id"] if isinstance(row, sqlite3.Row) else row[0]
            client_name = row["name"] if isinstance(row, sqlite3.Row) else row[1]

            if client_name not in disk_clients:
                # This client's folder was deleted — remove from DB.
                cur.execute(
                    """
                    DELETE FROM document_fields
                    WHERE document_id IN (SELECT id FROM documents WHERE client_id = ?)
                    """,
                    (client_id,),
                )
                cur.execute(
                    "DELETE FROM compliance_records WHERE client_id = ?", (client_id,)
                )
                cur.execute(
                    "DELETE FROM documents WHERE client_id = ?", (client_id,)
                )
                cur.execute(
                    "DELETE FROM tenants WHERE client_id = ?", (client_id,)
                )
                cur.execute(
                    "DELETE FROM properties WHERE client_id = ?", (client_id,)
                )
                cur.execute("DELETE FROM clients WHERE id = ?", (client_id,))
                print(f"Cleaned up stale client from portal: {client_name}")

        conn.commit()
    finally:
        conn.close()


def ensure_compliance_actions_table():
    """Create compliance_actions table if it does not exist (inline migration at startup)."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS compliance_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                property_id INTEGER NOT NULL,
                comp_type TEXT NOT NULL,
                status TEXT NOT NULL,
                snoozed_until TEXT,
                resolved_at TEXT,
                resolved_by TEXT,
                notes TEXT,
                created_at TEXT,
                UNIQUE(client_id, property_id, comp_type)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def ensure_activity_log_table():
    """Create activity_log table if it does not exist (inline migration at startup)."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                description TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def log_activity(
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    description: str | None = None,
    metadata: str | dict | None = None,
    client_id: int | None = None,
    user_id: int | None = None,
) -> None:
    """
    Insert an activity log entry.
    action: e.g. 'document_uploaded', 'compliance_resolved', 'user_login'
    If client_id/user_id not provided, they are derived from current request (get_current_client, current_user).
    """
    try:
        if user_id is None and current_user.is_authenticated:
            uid = getattr(current_user, "id", None)
            user_id = int(uid) if uid is not None else None
    except Exception:
        user_id = None
    if client_id is None:
        name = get_current_client() if current_user.is_authenticated else None
        if name:
            row = query_db("SELECT id FROM clients WHERE name = ?", (name,), one=True)
            client_id = int(row["id"]) if row else None
        else:
            client_id = None
    meta_str = None
    if metadata is not None:
        meta_str = json.dumps(metadata) if isinstance(metadata, dict) else str(metadata)
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO activity_log (client_id, user_id, action, entity_type, entity_id, description, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (client_id, user_id, action, entity_type, entity_id, description or None, meta_str),
        )
        conn.commit()
    finally:
        conn.close()


def _parse_date(value: str):
    """Best-effort date parser for compliance expiry fields."""
    if not value:
        return None
    value = value.strip()
    if not value:
        return None

    # Try a set of common formats seen in review.json / document_fields.
    formats = [
        "%Y-%m-%d",        # 2026-03-15
        "%d/%m/%Y",        # 15/03/2026
        "%d-%m-%Y",        # 15-03-2026
        "%d %b %Y",        # 15 Mar 2026
        "%d %B %Y",        # 15 March 2026
        "%Y/%m/%d",        # 2026/03/15
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    # Fallback: let datetime try its own parser; if it fails, return None.
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.date()
    except Exception:
        return None


# Document types and their expiry field priorities for per-document compliance.
COMPLIANCE_EXPIRY_FIELDS = {
    "gas-safety-certificate": ["expiry_date", "next_inspection_date"],
    "gas_safety_certificate": ["expiry_date", "next_inspection_date"],
    "eicr": ["next_inspection_date", "expiry_date"],
    "epc": ["valid_until", "expiry_date"],
    "deposit-protection": ["expiry_date", "valid_until"],
    "deposit_protection_certificate": ["expiry_date", "valid_until"],
}

# Mapping from compliance engine keys to document_types.key + labels.
COMPLIANCE_TYPE_META = {
    "gas_safety": {
        "slug": "gas-safety-certificate",
        "label": "Gas Safety Certificate",
    },
    "eicr": {
        "slug": "eicr",
        "label": "EICR",
    },
    "epc": {
        "slug": "epc",
        "label": "EPC",
    },
    "deposit": {
        "slug": "deposit-protection",
        "label": "Deposit Protection Certificate",
    },
}


def get_compliance_status_for_doc(doc_type_key: str, fields_dict: dict[str, str]):
    """
    Given a document type key and its fields, return per-document compliance status.

    Returns (status, expiry_date_str, days_until_expiry) where:
      - status: "valid" | "expired" | "expiring_soon" | "no_expiry" | None
      - expiry_date_str: ISO string "YYYY-MM-DD" or original string, or None
      - days_until_expiry: int (negative if expired) or None
    """
    key_lower = (doc_type_key or "").strip().lower().replace(" ", "_").replace("-", "_")

    # Find matching compliance config (supports slight key variations).
    expiry_fields = None
    for config_key, field_list in COMPLIANCE_EXPIRY_FIELDS.items():
        config_normalized = config_key.lower().replace(" ", "_").replace("-", "_")
        if config_normalized in key_lower or key_lower in config_normalized:
            expiry_fields = field_list
            break

    if not expiry_fields:
        # Not a compliance-tracked document type.
        return None, None, None

    # Look for expiry date in priority order.
    expiry_str = None
    for field_key in expiry_fields:
        raw = (fields_dict.get(field_key) or "").strip()
        if raw:
            expiry_str = raw
            break

    if not expiry_str:
        # Has compliance tracking but no expiry date recorded.
        return "no_expiry", None, None

    expiry_date = _parse_date(expiry_str)
    if not expiry_date:
        # Could not parse the date string; surface raw string but treat as no_expiry.
        return "no_expiry", expiry_str, None

    today = date.today()
    days_until = (expiry_date - today).days

    if days_until < 0:
        return "expired", expiry_date.isoformat(), days_until
    if days_until <= 30:
        return "expiring_soon", expiry_date.isoformat(), days_until
    return "valid", expiry_date.isoformat(), days_until


def _flatten_fields(structured_fields: dict) -> dict[str, str]:
    """
    Convert structured fields ({ key: {label, value} }) into a flat key->value dict.
    """
    if not structured_fields:
        return {}
    flat: dict[str, str] = {}
    for key, meta in structured_fields.items():
        if isinstance(meta, dict):
            flat[key] = (meta.get("value") or "").strip()
        else:
            flat[key] = (meta or "").strip()
    return flat


def _build_property_compliance_and_deadlines(docs: list[dict]) -> tuple[dict, list[dict]]:
    """
    Build detailed per-type compliance metadata and an ordered deadlines list
    for a single property's documents.
    """
    today = date.today()
    compliance_detail: dict[str, dict] = {}
    deadlines: list[dict] = []

    # Index documents by doc_type_slug for quick lookup.
    docs_by_slug: dict[str, list[dict]] = {}
    for d in docs:
        slug = (d.get("doc_type_slug") or "").strip()
        if not slug:
            continue
        docs_by_slug.setdefault(slug, []).append(d)

    def _latest_doc(candidates: list[dict]) -> dict | None:
        if not candidates:
            return None

        def _key(doc: dict):
            # Use same ordering as elsewhere: batch_date > scanned_at > reviewed_at
            for field in ("batch_date", "scanned_at", "reviewed_at"):
                val = doc.get(field)
                if val:
                    return val
            return ""

        return max(candidates, key=_key)

    def _severity_text(type_key: str, status: str, days: int | None) -> str | None:
        if status == "expired":
            if type_key == "gas_safety":
                return "Landlord liable for £6,000 fine"
            if type_key == "eicr":
                return "Landlord liable for up to £30,000 fine"
            if type_key == "epc":
                return "Required for all rental properties"
            if type_key == "deposit":
                return "Tenant may claim up to 3x deposit"
        if status == "valid" and days is not None:
            return f"{days} days remaining"
        return None

    for type_key, meta in COMPLIANCE_TYPE_META.items():
        slug = meta["slug"]
        label = meta["label"]
        candidates = docs_by_slug.get(slug, [])
        latest = _latest_doc(candidates)

        status: str
        expiry_iso: str | None
        days_until: int | None
        display_text: str
        action: str | None = None
        extra: str | None = None
        doc_id: str | None = None

        if latest:
            structured_fields = latest.get("fields") or {}
            flat_fields = _flatten_fields(structured_fields)
            s, expiry_iso, days_until = get_compliance_status_for_doc(slug, flat_fields)
            # Map "no_expiry" / None to valid-but-no-date.
            if not s or s == "no_expiry":
                status = "valid"
                expiry_iso = None
                days_until = None
                display_text = "No expiry date recorded"
            else:
                status = s
                if days_until is None:
                    display_text = "Expiry date unknown"
                elif days_until < 0:
                    display_text = f"Expired {abs(days_until)} days ago"
                elif days_until <= 30:
                    display_text = f"Expires in {days_until} days"
                else:
                    display_text = f"Expires in {days_until} days"

            # Action text
            if status == "expired":
                if type_key == "gas_safety":
                    action = "Action required: arrange gas safety inspection"
                elif type_key == "eicr":
                    action = "Action required: arrange electrical inspection"
                elif type_key == "epc":
                    action = "Action required: arrange EPC assessment"
                elif type_key == "deposit":
                    action = "Action required: upload deposit protection certificate"
            elif status == "expiring_soon":
                action = "Due for renewal within 30 days"

            # EPC extra rating text
            if type_key == "epc":
                current_rating = flat_fields.get("current_rating") or ""
                potential_rating = flat_fields.get("potential_rating") or ""
                if current_rating and potential_rating:
                    extra = f"Rating {current_rating} ({potential_rating} potential)"
                elif current_rating:
                    extra = f"Rating {current_rating}"

            doc_id = latest.get("source_doc_id") or None
        else:
            # No document of this type for this property.
            status = "missing"
            expiry_iso = None
            days_until = None
            display_text = "No certificate on file"
            if type_key == "deposit":
                action = "Action required: upload deposit protection certificate"
            else:
                action = f"Action required: upload {label.lower()}"
            doc_id = None

        detail = {
            "status": status,
            "expiry_date": expiry_iso,
            "days_until_expiry": days_until,
            "display_text": display_text,
            "action": action,
            "doc_id": doc_id,
        }
        if type_key == "epc":
            detail["extra"] = extra

        compliance_detail[type_key] = detail

        # Build deadlines entry (one per compliance type).
        deadline = {
            "type": label,
            "status": status,
            "expiry_date": expiry_iso,
            "days": days_until,
            "display_text": display_text
            if expiry_iso is None
            else (
                # For deadlines list, be explicit with date when present.
                f"{display_text} · {expiry_iso}"
            ),
            "severity_text": _severity_text(type_key, status, days_until),
            "doc_id": doc_id,
        }
        deadlines.append(deadline)

    # Sort deadlines: expired (most overdue first), then expiring_soon, then valid, then missing.
    def _deadline_sort_key(item: dict):
        status = item.get("status") or ""
        days = item.get("days")
        if status == "expired":
            bucket = 0
        elif status == "expiring_soon":
            bucket = 1
        elif status == "valid":
            bucket = 2
        else:
            bucket = 3
        # For expired we want most negative first; for others, smallest positive first; None last.
        if days is None:
            secondary = 999999
        else:
            secondary = days
        return (bucket, secondary)

    deadlines.sort(key=_deadline_sort_key)

    return compliance_detail, deadlines


def _build_tenant_snapshot(docs: list[dict]) -> dict | None:
    """
    Build a simple "current tenant" snapshot from the latest Tenancy Agreement document.
    """
    tenancy_docs = [
        d for d in docs if (d.get("doc_type_slug") or "").strip().lower() == "tenancy-agreement"
    ]
    if not tenancy_docs:
        return None

    def _key(doc: dict):
        for field in ("batch_date", "scanned_at", "reviewed_at"):
            val = doc.get(field)
            if val:
                return val
        return ""

    latest = max(tenancy_docs, key=_key)
    structured_fields = latest.get("fields") or {}
    flat_fields = _flatten_fields(structured_fields)

    name = flat_fields.get("tenant_full_name") or ""
    start_raw = flat_fields.get("start_date") or ""
    end_raw = flat_fields.get("end_date") or ""
    rent = flat_fields.get("monthly_rent_amount") or ""
    deposit = flat_fields.get("deposit_amount") or ""

    end_date = _parse_date(end_raw) if end_raw else None
    if end_date:
        today = date.today()
        if end_date >= today:
            is_current: bool | None = True
            status_text = "Active tenancy"
        else:
            is_current = False
            status_text = "Tenancy ended"
    else:
        is_current = None
        status_text = "End date unknown"

    return {
        "name": name or None,
        "tenancy_start": start_raw or None,
        "tenancy_end": end_raw or None,
        "rent": rent or None,
        "deposit": deposit or None,
        "is_current": is_current,
        "status_text": status_text,
    }


# ── UI Routes ────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET"])
def login():
    if current_user.is_authenticated:
        return (
            jsonify({"redirect": "/"}),
            302,
        ) if request.is_json else (
            "", 302, {"Location": "/"}
        )
    return render_template("login.html", error=None)


@app.route("/login", methods=["POST"])
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not email or not password:
        return render_template("login.html", error="Please enter email and password.")

    conn = get_db()
    try:
        cur = conn.execute(
            """
            SELECT id, email, full_name, role, client_id, password_hash, is_active
            FROM users
            WHERE LOWER(email) = ?
            """,
            (email,),
        )
        row = cur.fetchone()
        if not row:
            return render_template("login.html", error="Invalid email or password.")

        if not row["is_active"]:
            return render_template("login.html", error="Account is disabled.")

        if not check_password_hash(row["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")

        user = User(
            user_id=row["id"],
            email=row["email"],
            full_name=row["full_name"],
            role=row["role"],
            client_id=row["client_id"],
            is_active=row["is_active"],
        )
        login_user(user)

        # Update last_login timestamp
        now = datetime.utcnow().isoformat(timespec="seconds")
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (now, row["id"]),
        )
        conn.commit()
    finally:
        conn.close()

    log_activity("user_login", description=f"{email} logged in", user_id=row["id"])
    return "", 302, {"Location": "/"}


@app.route("/logout")
def logout():
    logout_user()
    return "", 302, {"Location": "/login"}


@app.route("/")
@login_required
def index():
    """Main portal page — search-first document archive."""
    client = get_current_client()
    # #region agent log
    try:
        import time as _time  # local import to avoid clashes
        with open("debug-c11422.log", "a", encoding="utf-8") as _f:
            _f.write(json.dumps({
                "sessionId": "c11422",
                "runId": "pre-fix",
                "hypothesisId": "H3",
                "location": "portal_new/app.py:index",
                "message": "portal_new index route hit",
                "data": {
                    "client": bool(client),
                },
                "timestamp": int(_time.time() * 1000),
            }) + "\n")
    except Exception:
        pass
    # #endregion agent log
    return render_template(
        "portal.html",
        client_name=client or None,
        active_view="archive",
        show_client_picker=not bool(client) and getattr(current_user, "role", None) == "admin",
        user_full_name=getattr(current_user, "full_name", None),
        user_email=getattr(current_user, "email", None),
        user_role=getattr(current_user, "role", None),
    )


@app.route("/compliance")
@login_required
def compliance_dashboard():
    """
    Compliance dashboard page.

    Example: /compliance?client=Client1
    """
    client = get_current_client() or ""

    try:
        data = compliance_engine.evaluate_compliance()
    except Exception as e:
        # Render a minimal error page rather than crashing the server.
        return (
            f"<h1 style='color:#f87171;font-family:sans-serif'>Compliance error</h1>"
            f"<p style='font-family:sans-serif;color:#e5e7eb;background:#020617'>"
            f"{type(e).__name__}: {str(e)}</p>",
            500,
        )

    if client:
        properties = [row for row in data if (row.get("client") or "").strip() == client]
    else:
        properties = data

    # Attach portal.properties.id to each compliance row so the dashboard
    # can link through to the property detail page.
    enriched_properties = []
    conn = get_db()
    try:
        for row in properties:
            name = (row.get("client") or "").strip()
            address = (row.get("property") or "").strip()
            prop_id = None
            if name and address:
                cur = conn.execute(
                    """
                    SELECT p.id
                    FROM properties p
                    JOIN clients c ON p.client_id = c.id
                    WHERE c.name = ? AND p.address = ?
                    LIMIT 1
                    """,
                    (name, address),
                )
                r = cur.fetchone()
                if r:
                    prop_id = r[0]
            row["property_id"] = prop_id
            enriched_properties.append(row)
    finally:
        conn.close()

    alerts = compliance_engine.build_summary(properties)

    # Portfolio compliance summary.
    #
    # Definition (kept intentionally simple and transparent):
    #   - Tracked compliance document types per property:
    #       gas_safety, eicr, epc, deposit
    #   - total_checks  = number of returned properties * 4
    #   - compliant     = count of statuses equal to "valid"
    #   - expired       = count of statuses equal to "expired"
    #   - missing       = count of statuses equal to "missing"
    #   - expiring_soon = count of statuses equal to "expiring_soon"
    #   - percent_compliant = (compliant / total_checks) * 100 (0 when total_checks == 0)
    total_checks = 0
    compliant_checks = 0
    expired_count = 0
    missing_count = 0
    expiring_soon_count = 0

    for row in enriched_properties:
        for key in ("gas_safety", "eicr", "epc", "deposit"):
            status = (row.get(key) or "").strip().lower()
            if not status:
                continue
            total_checks += 1
            if status == "valid":
                compliant_checks += 1
            elif status == "expired":
                expired_count += 1
            elif status == "missing":
                missing_count += 1
            elif status == "expiring_soon":
                expiring_soon_count += 1

    percent_compliant = (compliant_checks / total_checks * 100.0) if total_checks else 0.0

    summary = {
        "total_checks": total_checks,
        "compliant_checks": compliant_checks,
        "percent_compliant": percent_compliant,
        "expired_count": expired_count,
        "missing_count": missing_count,
        "expiring_soon_count": expiring_soon_count,
    }

    return render_template(
        "compliance.html",
        client_name=client or None,
        properties=enriched_properties,
        alerts=alerts,
        active_view="compliance",
        summary=summary,
    )


@app.route("/property/<int:property_id>")
@login_required
def property_detail(property_id: int):
    """
    Property detail page.

    Shows compliance + all related documents for a single property.
    """
    prop = query_db(
        """
        SELECT
            p.id AS property_id,
            p.address AS property_address,
            c.name AS client_name
        FROM properties p
        JOIN clients c ON p.client_id = c.id
        WHERE p.id = ?
        """,
        (property_id,),
        one=True,
    )

    if not prop:
        abort(404, description="Property not found")

    return render_template(
        "property.html",
        property_id=prop["property_id"],
        property_address=prop["property_address"],
        client_name=prop["client_name"],
    )


def _document_view_render(source_doc_id: str, client_name: str, document_db_id: int | None = None):
    return render_template(
        "document_view.html",
        source_doc_id=source_doc_id,
        client_name=client_name,
        document_db_id=document_db_id,
        active_view="archive",
        user_full_name=getattr(current_user, "full_name", None),
        user_email=getattr(current_user, "email", None),
        user_role=getattr(current_user, "role", None),
    )


@app.route("/document/by-id/<int:doc_id>")
@login_required
def document_view_by_id(doc_id: int):
    """
    Full-page document viewer keyed by portal documents.id (stable; avoids source_doc_id mismatches).
    """
    row = query_db(
        """
        SELECT d.source_doc_id, c.name AS client_name
        FROM documents d
        JOIN clients c ON d.client_id = c.id
        WHERE d.id = ?
        """,
        (doc_id,),
        one=True,
    )
    if not row:
        abort(404, description="Document not found")

    client_scope = get_current_client() or ""
    cn = (row.get("client_name") or "").strip()
    if client_scope and _norm_client_name(cn) != _norm_client_name(client_scope):
        abort(404, description="Document not found")

    sid = (row.get("source_doc_id") or "").strip()
    if not sid:
        abort(404, description="Document not found")

    return _document_view_render(sid, cn, document_db_id=doc_id)


@app.route("/document/<path:source_doc_id>")
@login_required
def document_view_page(source_doc_id: str):
    """
    Full-page document viewer: summary column + PDF (opened from Archive in a new tab).
    Matches source_doc_id case-insensitively after trim (ScanStation IDs are not always uniform in DB).
    """
    raw = (source_doc_id or "").strip()
    if not raw:
        abort(404, description="Document not found")

    row = query_db(
        """
        SELECT d.id, d.source_doc_id, c.name AS client_name
        FROM documents d
        JOIN clients c ON d.client_id = c.id
        WHERE LOWER(TRIM(d.source_doc_id)) = LOWER(TRIM(?))
        """,
        (raw,),
        one=True,
    )
    if not row:
        abort(404, description="Document not found")

    client_scope = get_current_client() or ""
    cn = (row.get("client_name") or "").strip()
    if client_scope and _norm_client_name(cn) != _norm_client_name(client_scope):
        abort(404, description="Document not found")

    sid = (row.get("source_doc_id") or "").strip()
    db_id = row.get("id")
    return _document_view_render(sid, cn, document_db_id=db_id if isinstance(db_id, int) else None)


@app.route("/settings")
@login_required
def settings_page():
    """Settings page — account, notifications, team (admin), portal prefs, danger zone (admin)."""
    client = get_current_client() or ""
    is_admin = getattr(current_user, "role", None) == "admin"
    return render_template(
        "settings.html",
        active_view="settings",
        client_name=client or None,
        user_email=getattr(current_user, "email", None) or "",
        user_full_name=getattr(current_user, "full_name", None) or "",
        user_role=getattr(current_user, "role", None) or "user",
        is_admin=is_admin,
    )


@app.route("/activity")
@login_required
def activity_page():
    """Activity log page — timeline of portal events."""
    client = get_current_client() or ""
    return render_template(
        "activity.html",
        active_view="activity",
        client_name=client or None,
    )


@app.route("/ai-chat")
@login_required
def ai_chat_page():
    client = get_current_client() or ""
    return render_template(
        "ai_chat.html",
        active_view="ai_chat",
        client_name=client or None,
    )


@app.route("/pdf/<path:pdf_path>")
def serve_pdf(pdf_path):
    """Serve a PDF file from the filesystem (legacy path-based route)."""
    candidates = [
        pdf_path,
        os.path.join(BASE_DIR, "..", pdf_path),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return send_file(path, mimetype="application/pdf")
    abort(404, description="PDF not found")


@app.route("/pdf-by-id/<source_doc_id>")
def serve_pdf_by_id(source_doc_id: str):
    """
    Serve a PDF by looking up its path in portal.db using source_doc_id.
    This avoids fragile URL-encoding of full Windows paths.
    """
    doc = query_db(
        "SELECT pdf_path FROM documents WHERE source_doc_id = ?",
        (source_doc_id,),
        one=True,
    )
    if not doc:
        abort(404, description="Document not found")

    raw_path = (doc.get("pdf_path") or "").strip()
    if not raw_path:
        abort(404, description="PDF path missing")

    candidates = []

    # If the DB path is already absolute, try it directly
    candidates.append(raw_path)

    # Also try relative to project root just in case
    candidates.append(os.path.join(BASE_DIR, "..", raw_path))

    for path in candidates:
        if os.path.isfile(path):
            return send_file(path, mimetype="application/pdf")

    abort(404, description="PDF not found")


# ── API Routes ───────────────────────────────────────────────────────────────
@app.route("/api/properties")
@login_required
def api_properties():
    """
    Property-first archive view.

    Returns one row per property with:
      - property_id
      - property_address
      - client_name
      - total_documents
      - latest_activity_date
      - gas_safety / eicr / epc / deposit compliance statuses
    """
    client = get_current_client() or ""

    sql = """
        SELECT
            p.id AS property_id,
            p.address AS property_address,
            c.name AS client_name,
            COUNT(d.id) AS total_documents,
            MAX(
                COALESCE(
                    d.batch_date,
                    d.scanned_at,
                    d.reviewed_at,
                    d.imported_at
                )
            ) AS latest_activity_date
        FROM properties p
        JOIN clients c ON p.client_id = c.id
        LEFT JOIN documents d ON d.property_id = p.id
        WHERE 1=1
    """
    args = []

    if client:
        sql += " AND c.name = ?"
        args.append(client)

    sql += """
        GROUP BY
            p.id,
            p.address,
            c.name
        ORDER BY
            latest_activity_date DESC
    """

    properties = query_db(sql, args)

    # Enrich with compliance statuses using the existing engine so we keep
    # compliance logic in one place.
    try:
        compliance_rows = compliance_engine.evaluate_compliance()
    except Exception:
        # If compliance evaluation fails for any reason, we still want the
        # property list to work; default all statuses to "missing".
        compliance_rows = []

    compliance_index = {}
    for row in compliance_rows:
        key = (
            (row.get("client") or "").strip(),
            (row.get("property") or "").strip(),
        )
        compliance_index[key] = {
            "gas_safety": row.get("gas_safety", "missing"),
            "eicr": row.get("eicr", "missing"),
            "epc": row.get("epc", "missing"),
            "deposit": row.get("deposit", "missing"),
        }

    for prop in properties:
        key = (
            (prop.get("client_name") or "").strip(),
            (prop.get("property_address") or "").strip(),
        )
        comp = compliance_index.get(
            key,
            {
                "gas_safety": "missing",
                "eicr": "missing",
                "epc": "missing",
                "deposit": "missing",
            },
        )
        prop.update(comp)

    return jsonify({"properties": properties, "count": len(properties)})


@app.route("/api/clients")
@login_required
def api_clients():
    """
    List active clients for the portal client picker.

    Returns:
        {
          "clients": [
            { "id": 1, "name": "TestClient", "slug": "testclient" },
            ...
          ]
        }
    """
    clients = query_db(
        """
        SELECT id, name, slug
        FROM clients
        WHERE is_active = 1
        ORDER BY name
        """
    )
    return jsonify({"clients": clients})


@app.route("/api/settings/notifications", methods=["POST"])
@login_required
def update_notification_settings():
    """Placeholder — update notification preferences (not persisted yet)."""
    return jsonify({"success": True})


@app.route("/api/settings/users")
@login_required
def api_settings_users():
    """List users for Settings > Team Members. Admin only."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Forbidden"}), 403
    users = query_db(
        """
        SELECT id, email, full_name, role, is_active
        FROM users
        ORDER BY full_name, email
        """
    )
    return jsonify({"users": users})


@app.route("/api/activity")
@login_required
def api_activity():
    """
    GET ?client=X&limit=50&offset=0&action=document_uploaded,compliance_resolved
    Returns most recent activity log entries, newest first.
    action: optional comma-separated list to filter by (e.g. document_uploaded, user_login).
    Each entry: id, action, entity_type, entity_id, description, created_at, user_name.
    """
    client_name = (request.args.get("client") or "").strip() or get_current_client() or ""
    try:
        limit = min(int(request.args.get("limit", 50)), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except (TypeError, ValueError):
        limit = 50
        offset = 0
    action_filter = (request.args.get("action") or "").strip()
    actions_list = [a.strip() for a in action_filter.split(",") if a.strip()] if action_filter else None
    client_id = None
    if client_name:
        row = query_db("SELECT id FROM clients WHERE name = ?", (client_name,), one=True)
        if row:
            client_id = row["id"]
        else:
            client_id = -1  # client name given but not found -> return no rows
    if client_id == -1:
        rows = []
    elif client_id is not None and actions_list:
        placeholders = ",".join("?" * len(actions_list))
        sql = f"""
            SELECT a.id, a.action, a.entity_type, a.entity_id, a.description, a.created_at,
                   u.full_name AS user_name
            FROM activity_log a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.client_id = ? AND a.action IN ({placeholders})
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
            """
        rows = query_db(sql, (client_id, *actions_list, limit + 1, offset))
    elif client_id is not None:
        rows = query_db(
            """
            SELECT a.id, a.action, a.entity_type, a.entity_id, a.description, a.created_at,
                   u.full_name AS user_name
            FROM activity_log a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.client_id = ?
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (client_id, limit + 1, offset),
        )
    elif actions_list:
        placeholders = ",".join("?" * len(actions_list))
        sql = f"""
            SELECT a.id, a.action, a.entity_type, a.entity_id, a.description, a.created_at,
                   u.full_name AS user_name
            FROM activity_log a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.action IN ({placeholders})
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
            """
        rows = query_db(sql, (*actions_list, limit + 1, offset))
    else:
        rows = query_db(
            """
            SELECT a.id, a.action, a.entity_type, a.entity_id, a.description, a.created_at,
                   u.full_name AS user_name
            FROM activity_log a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit + 1, offset),
        )
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    entries = [
        {
            "id": r["id"],
            "action": r["action"],
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "description": r["description"] or "",
            "created_at": r["created_at"] or "",
            "user_name": (r["user_name"] or "").strip() or None,
        }
        for r in rows
    ]
    return jsonify({"entries": entries, "has_more": has_more})


@app.route("/api/clients/<int:client_id>", methods=["DELETE"])
@login_required
def delete_client(client_id: int):
    """Delete a client and all their data from portal.db."""
    conn = get_db()
    try:
        cur = conn.cursor()

        # Get client name for logging
        cur.execute("SELECT id, name FROM clients WHERE id = ?", (client_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Client not found"}), 404

        # sqlite3.Row or tuple both support index access.
        client_name = row["name"] if isinstance(row, sqlite3.Row) else row[1]

        # 1. document_fields (references documents)
        cur.execute(
            """
            DELETE FROM document_fields
            WHERE document_id IN (SELECT id FROM documents WHERE client_id = ?)
            """,
            (client_id,),
        )

        # 2. compliance_records (references documents and properties)
        cur.execute("DELETE FROM compliance_records WHERE client_id = ?", (client_id,))

        # 3. documents (references properties and clients)
        cur.execute("DELETE FROM documents WHERE client_id = ?", (client_id,))

        # 4. tenants (references properties and clients)
        cur.execute("DELETE FROM tenants WHERE client_id = ?", (client_id,))

        # 5. properties (references clients)
        cur.execute("DELETE FROM properties WHERE client_id = ?", (client_id,))

        # 6. client itself
        cur.execute("DELETE FROM clients WHERE id = ?", (client_id,))

        conn.commit()
    finally:
        conn.close()

    return jsonify(
        {
            "success": True,
            "message": f'Deleted client "{client_name}" and all associated data from portal',
        }
    )


@app.route("/api/properties/<int:property_id>")
@login_required
def api_property_detail(property_id: int):
    """
    Detailed snapshot for a single property.

    Includes:
      - property address
      - client name
      - compliance snapshot (gas_safety, eicr, epc, deposit)
      - all related documents (with fields)
      - documents grouped by document type
      - latest document activity date
    """
    prop = query_db(
        """
        SELECT
            p.id AS property_id,
            p.address AS property_address,
            c.name AS client_name
        FROM properties p
        JOIN clients c ON p.client_id = c.id
        WHERE p.id = ?
        """,
        (property_id,),
        one=True,
    )

    if not prop:
        abort(404, description="Property not found")

    client_scope = get_current_client() or ""
    if client_scope and (prop.get("client_name") or "").strip() != client_scope:
        abort(404, description="Property not found")

    # Load all documents for this property
    docs = query_db(
        """
        SELECT
            d.id,
            d.source_doc_id,
            d.doc_name,
            d.status,
            d.pdf_path,
            d.quality_score,
            d.reviewed_by,
            d.reviewed_at,
            d.scanned_at,
            d.batch_date,
            dt.label AS doc_type,
            dt.key AS doc_type_slug,
            c.name AS client_name,
            p.address AS property_address
        FROM documents d
        LEFT JOIN document_types dt ON d.document_type_id = dt.id
        LEFT JOIN clients c ON d.client_id = c.id
        LEFT JOIN properties p ON d.property_id = p.id
        WHERE p.id = ?
        ORDER BY
            dt.label ASC,
            COALESCE(d.batch_date, d.scanned_at, d.reviewed_at) DESC
        """,
        (property_id,),
    )

    # Attach fields for each document, reusing the same pattern as /api/documents.
    conn = get_db()
    try:
        for doc in docs:
            cur = conn.execute(
                "SELECT field_key, field_label, field_value FROM document_fields WHERE document_id = ?",
                (doc["id"],),
            )
            doc["fields"] = {
                row["field_key"]: {
                    "label": row["field_label"]
                    or row["field_key"].replace("_", " ").title(),
                    "value": row["field_value"] or "",
                }
                for row in cur.fetchall()
            }
    finally:
        conn.close()

    # Attach convenience fields and compute latest activity date.
    latest_activity = None
    for doc in docs:
        # doc_id mirrors source_doc_id for a simpler frontend contract.
        doc["doc_id"] = doc.get("source_doc_id")

        client = (doc.get("client_name") or "").strip()
        source_doc_id = (doc.get("source_doc_id") or "").strip()
        if client and source_doc_id:
            safe_client = quote(client)
            safe_doc = quote(source_doc_id)
            doc["pdf_url"] = (
                f"http://127.0.0.1:8765/pdf/{safe_client}/{safe_doc}#toolbar=0&navpanes=0&page=1&zoom=page-width"
            )
        else:
            doc["pdf_url"] = None

        # Per-document compliance metadata for property detail view.
        # Flatten the structured fields ({ key: {label, value} }) into a simple key → value dict.
        structured_fields = doc.get("fields") or {}
        flat_fields = _flatten_fields(structured_fields)
        status, expiry_str, days_until = get_compliance_status_for_doc(
            doc.get("doc_type_slug") or "", flat_fields
        )
        doc["compliance_status"] = status
        doc["expiry_date"] = expiry_str
        doc["days_until_expiry"] = days_until

        # Key fields summary for inline display on document cards.
        doc_type_slug = (doc.get("doc_type_slug") or "").strip().lower()
        summary: str | None = None

        if doc_type_slug in ("gas-safety-certificate", "gas_safety_certificate"):
            engineer = flat_fields.get("engineer_name") or ""
            gas_safe = flat_fields.get("gas_safe_reg") or ""
            parts = []
            if engineer:
                parts.append(f"Inspected by: {engineer}")
            if gas_safe:
                parts.append(f"Gas Safe #{gas_safe}")
            summary = " · ".join(parts) if parts else None
        elif doc_type_slug == "eicr":
            result = flat_fields.get("overall_result") or ""
            electrician = flat_fields.get("electrician_name") or ""
            parts = []
            if result:
                parts.append(f"Result: {result}")
            if electrician:
                parts.append(f"By: {electrician}")
            summary = " · ".join(parts) if parts else None
        elif doc_type_slug == "epc":
            current_rating = flat_fields.get("current_rating") or ""
            potential_rating = flat_fields.get("potential_rating") or ""
            if current_rating and potential_rating:
                summary = f"Rating: {current_rating} ({potential_rating} potential)"
            elif current_rating:
                summary = f"Rating: {current_rating}"
        elif doc_type_slug == "tenancy-agreement":
            tenant = flat_fields.get("tenant_full_name") or ""
            start = flat_fields.get("start_date") or ""
            end = flat_fields.get("end_date") or ""
            parts = []
            if tenant:
                parts.append(f"Tenant: {tenant}")
            if start or end:
                dates = f"{start or '?'} — {end or '?'}"
                parts.append(dates)
            summary = " · ".join(parts) if parts else None
        elif doc_type_slug in ("deposit-protection", "deposit_protection_certificate"):
            scheme = flat_fields.get("scheme_name") or ""
            cert = flat_fields.get("certificate_number") or ""
            parts = []
            if scheme:
                parts.append(f"Scheme: {scheme}")
            if cert:
                parts.append(f"Cert #{cert}")
            summary = " · ".join(parts) if parts else None

        doc["key_fields_summary"] = summary

        candidate = (
            doc.get("batch_date")
            or doc.get("scanned_at")
            or doc.get("reviewed_at")
        )
        if candidate and (latest_activity is None or candidate > latest_activity):
            latest_activity = candidate

    # Enrich with compliance snapshot using the existing engine.
    compliance_detail, deadlines = _build_property_compliance_and_deadlines(docs)

    gas_safety = compliance_detail.get("gas_safety", {})
    eicr = compliance_detail.get("eicr", {})
    epc = compliance_detail.get("epc", {})
    deposit = compliance_detail.get("deposit", {})

    # Group documents by document type label for easier rendering.
    documents_by_type = {}
    for doc in docs:
        key = doc.get("doc_type") or "Other"
        documents_by_type.setdefault(key, []).append(doc)

    prop_detail = {
        "property_id": prop["property_id"],
        "property_address": prop["property_address"],
        "client_name": prop["client_name"],
        "latest_activity_date": latest_activity,
        "gas_safety": gas_safety,
        "eicr": eicr,
        "epc": epc,
        "deposit": deposit,
        "deadlines": deadlines,
        "tenant": _build_tenant_snapshot(docs),
        "documents": docs,
        "documents_by_type": documents_by_type,
    }

    # For convenience, also expose documents at the top level so callers that
    # don't need the grouped view can access them directly.
    return jsonify({"property": prop_detail, "documents": docs})


def _generate_property_pdf(prop_detail: dict) -> io.BytesIO:
    """Generate property pack summary PDF from prop_detail (same structure as api_property_detail)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=20 * mm, bottomMargin=22 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name="ReportTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    heading_style = ParagraphStyle(name="ReportHeading", parent=styles["Heading2"], fontSize=12, spaceAfter=6)
    normal = styles["Normal"]
    footer_text = "Generated %s by MorphIQ — Not just scanned, understood." % date.today().strftime("%d %b %Y")

    story = []
    story.append(Paragraph("MorphIQ Property Pack Summary", title_style))
    story.append(Paragraph(f"Property: {prop_detail.get('property_address') or '—'}", normal))
    story.append(Paragraph(f"Client: {prop_detail.get('client_name') or '—'}", normal))
    story.append(Paragraph(f"Date generated: {date.today().strftime('%d %B %Y')}", normal))
    story.append(Paragraph("Prepared by MorphIQ — morphiq.co.uk", normal))
    story.append(Spacer(1, 8 * mm))

    green = colors.HexColor("#22c55e")
    amber = colors.HexColor("#f59e0b")
    red = colors.HexColor("#ef4444")
    grey = colors.HexColor("#6b7280")

    # Compliance section
    story.append(Paragraph("Compliance status", heading_style))
    comp_data = [["Certificate", "Status", "Expiry / Notes"]]
    for key, label in [("gas_safety", "Gas Safety"), ("eicr", "EICR"), ("epc", "EPC"), ("deposit", "Deposit")]:
        d = prop_detail.get(key) or {}
        st = (d.get("status") or "missing").strip()
        display = d.get("display_text") or (st.replace("_", " ").title())
        if st == "valid":
            comp_data.append([label, "Valid", d.get("expiry_date") or "—"])
        elif st == "expiring_soon":
            comp_data.append([label, "Expiring soon", display])
        elif st == "expired":
            comp_data.append([label, "Expired", display])
        else:
            comp_data.append([label, "Missing", "No certificate on file"])
    t = Table(comp_data, colWidths=[45 * mm, 35 * mm, 80 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a3b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#374151")),
    ]))
    story.append(t)
    story.append(Spacer(1, 8 * mm))

    # Tenant
    tenant = prop_detail.get("tenant")
    story.append(Paragraph("Tenant information", heading_style))
    if tenant:
        story.append(Paragraph(f"Name: {tenant.get('name') or '—'}", normal))
        story.append(Paragraph(f"Tenancy: {tenant.get('tenancy_start') or '—'} to {tenant.get('tenancy_end') or '—'}", normal))
        story.append(Paragraph(f"Rent: {tenant.get('rent') or '—'} | Deposit: {tenant.get('deposit') or '—'}", normal))
        story.append(Paragraph(f"Status: {tenant.get('status_text') or '—'}", normal))
    else:
        story.append(Paragraph("No tenancy agreement on file.", normal))
    story.append(Spacer(1, 8 * mm))

    # Documents table
    story.append(Paragraph("Documents", heading_style))
    docs = prop_detail.get("documents") or []
    if not docs:
        story.append(Paragraph("No documents on file.", normal))
    else:
        doc_data = [["Type", "Date", "Status", "Key fields"]]
        for d in docs:
            dt = d.get("batch_date") or d.get("scanned_at") or d.get("reviewed_at") or "—"
            if dt and dt != "—":
                try:
                    dt = str(dt)[:10]
                except Exception:
                    pass
            doc_data.append([
                (d.get("doc_type") or "Document")[:25],
                str(dt)[:12],
                (d.get("status") or "—").replace("_", " ").title()[:12],
                (d.get("key_fields_summary") or "—")[:45],
            ])
        t2 = Table(doc_data, colWidths=[40 * mm, 25 * mm, 25 * mm, 70 * mm], repeatRows=1)
        t2.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a3b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#374151")),
        ]))
        story.append(t2)

    doc.build(story, onFirstPage=lambda canvas, doc: canvas.drawString(20 * mm, 15 * mm, footer_text), onLaterPages=lambda canvas, doc: canvas.drawString(20 * mm, 15 * mm, footer_text))
    buf.seek(0)
    return buf


@app.route("/api/properties/<int:property_id>/report")
@login_required
def api_property_report(property_id: int):
    """GET ?format=pdf — generate property pack summary PDF."""
    fmt = (request.args.get("format") or "").strip().lower()
    if fmt != "pdf":
        return jsonify({"error": "format=pdf required"}), 400
    prop = query_db(
        "SELECT p.id, p.address AS property_address, c.name AS client_name FROM properties p JOIN clients c ON p.client_id = c.id WHERE p.id = ?",
        (property_id,),
        one=True,
    )
    if not prop:
        abort(404, description="Property not found")
    client_scope = get_current_client() or ""
    if client_scope and (prop.get("client_name") or "").strip() != client_scope:
        abort(404, description="Property not found")
    docs = query_db(
        """SELECT d.id, d.source_doc_id, d.doc_name, d.status, d.batch_date, d.scanned_at, d.reviewed_at, dt.label AS doc_type, dt.key AS doc_type_slug
           FROM documents d LEFT JOIN document_types dt ON d.document_type_id = dt.id WHERE d.property_id = ?
           ORDER BY dt.label ASC, COALESCE(d.batch_date, d.scanned_at, d.reviewed_at) DESC""",
        (property_id,),
    )
    conn = get_db()
    try:
        for d in docs:
            cur = conn.execute("SELECT field_key, field_label, field_value FROM document_fields WHERE document_id = ?", (d["id"],))
            d["fields"] = {row["field_key"]: {"label": row["field_label"] or row["field_key"], "value": row["field_value"] or ""} for row in cur.fetchall()}
    finally:
        conn.close()
    for d in docs:
        flat = _flatten_fields(d.get("fields") or {})
        _, exp_str, days = get_compliance_status_for_doc(d.get("doc_type_slug") or "", flat)
        d["compliance_status"] = _
        d["expiry_date"] = exp_str
        d["days_until_expiry"] = days
        slug = (d.get("doc_type_slug") or "").strip().lower()
        if slug in ("gas-safety-certificate", "gas_safety_certificate"):
            d["key_fields_summary"] = " · ".join(filter(None, [flat.get("engineer_name"), flat.get("gas_safe_reg")]))
        elif slug == "eicr":
            d["key_fields_summary"] = " · ".join(filter(None, [flat.get("overall_result"), flat.get("electrician_name")]))
        elif slug == "epc":
            d["key_fields_summary"] = (flat.get("current_rating") or "") + (" (" + flat.get("potential_rating") + ")" if flat.get("potential_rating") else "")
        elif slug == "tenancy-agreement":
            d["key_fields_summary"] = " · ".join(filter(None, [flat.get("tenant_full_name"), flat.get("start_date"), flat.get("end_date")]))
        elif slug in ("deposit-protection", "deposit_protection_certificate"):
            d["key_fields_summary"] = " · ".join(filter(None, [flat.get("scheme_name"), flat.get("certificate_number")]))
        else:
            d["key_fields_summary"] = None
    compliance_detail, _ = _build_property_compliance_and_deadlines(docs)
    tenant = _build_tenant_snapshot(docs)
    prop_detail = {
        "property_address": prop["property_address"],
        "client_name": prop["client_name"],
        "gas_safety": compliance_detail.get("gas_safety", {}),
        "eicr": compliance_detail.get("eicr", {}),
        "epc": compliance_detail.get("epc", {}),
        "deposit": compliance_detail.get("deposit", {}),
        "tenant": tenant,
        "documents": docs,
    }
    buf = _generate_property_pdf(prop_detail)
    safe_addr = re.sub(r"[^\w\s-]", "", (prop["property_address"] or "")).strip()[:30] or "Property"
    filename = f"MorphIQ_Property_Report_{safe_addr}_{date.today().isoformat()}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=filename)


@app.route("/api/properties/<int:property_id>/download-pack", methods=["POST"])
@login_required
def api_property_download_pack(property_id: int):
    """
    Build a ZIP of all PDFs for this property, organized as <DocTypeLabel>/<filename>.pdf.
    Returns 404 JSON if no documents or no PDFs exist on disk.
    """
    clients_dir = get_clients_dir()

    prop = query_db(
        """
        SELECT p.id, p.address AS property_address, c.name AS client_name
        FROM properties p
        JOIN clients c ON p.client_id = c.id
        WHERE p.id = ?
        """,
        (property_id,),
        one=True,
    )
    if not prop:
        return jsonify({"error": "Property not found"}), 404

    client_scope = get_current_client() or ""
    if client_scope and (prop.get("client_name") or "").strip() != client_scope:
        return jsonify({"error": "Property not found"}), 404

    docs = query_db(
        """
        SELECT
            d.source_doc_id,
            d.pdf_path,
            dt.label AS doc_type_label,
            c.name AS client_name
        FROM documents d
        LEFT JOIN document_types dt ON d.document_type_id = dt.id
        LEFT JOIN clients c ON d.client_id = c.id
        WHERE d.property_id = ?
        """,
        (property_id,),
    )
    if not docs:
        return jsonify({"error": "No documents for this property"}), 404

    def safe_folder_name(s: str) -> str:
        return re.sub(r"[^\w\s-]", "", (s or "").strip()).strip() or "Other"

    entries = []
    for doc in docs:
        pdf_path = (doc.get("pdf_path") or "").strip()
        if not pdf_path:
            continue
        client_name = (doc.get("client_name") or "").strip()
        if not client_name:
            continue
        full_path = os.path.join(clients_dir, client_name, pdf_path)
        if not os.path.isfile(full_path):
            continue
        doc_type_label = safe_folder_name(doc.get("doc_type_label") or "Other")
        # Use source_doc_id for a unique filename; ensure .pdf extension
        base_name = (doc.get("source_doc_id") or "document").strip()
        if not base_name.lower().endswith(".pdf"):
            base_name += ".pdf"
        archive_path = f"{doc_type_label}/{base_name}"
        entries.append((archive_path, full_path))

    if not entries:
        return jsonify({"error": "No PDFs found on disk for this property"}), 404

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for archive_path, full_path in entries:
            zf.write(full_path, archive_path)

    buf.seek(0)
    safe_address = re.sub(r"[^a-zA-Z0-9]+", "_", (prop.get("property_address") or "Property").strip()).strip("_") or "Property"
    download_name = f"{safe_address}_Documents.zip"
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=download_name,
    )


@app.route("/api/documents")
@login_required
def api_documents():
    """
    Search and list documents.
    Query params:
        q       - search term
        type    - document type key filter
        status  - status filter
        sort    - 'newest' (default), 'oldest', 'name', 'status'
        limit   - max results (default 100)

    Scoped to the current client when one is active (manager: assigned client;
    admin: optional ?client= name). Matches archive /api/properties behaviour.
    """
    q = request.args.get("q", "").strip()
    doc_type = request.args.get("type", "").strip()
    status = request.args.get("status", "").strip()
    sort = request.args.get("sort", "newest").strip()
    limit = request.args.get("limit", "100").strip()

    try:
        limit = min(int(limit), 500)
    except ValueError:
        limit = 100

    client_scope = get_current_client() or ""

    sql = """
        SELECT
            d.id,
            d.property_id,
            d.source_doc_id,
            d.doc_name,
            d.status,
            d.pdf_path,
            d.quality_score,
            d.reviewed_by,
            d.reviewed_at,
            d.scanned_at,
            d.batch_date,
            COALESCE(d.batch_date, d.scanned_at, d.reviewed_at) AS imported_at,
            dt.label AS doc_type,
            dt.key AS doc_type_slug,
            c.name AS client_name,
            p.address AS property_address
        FROM documents d
        LEFT JOIN document_types dt ON d.document_type_id = dt.id
        LEFT JOIN clients c ON d.client_id = c.id
        LEFT JOIN properties p ON d.property_id = p.id
        WHERE 1=1
    """
    args = []

    if client_scope:
        sql += " AND c.name = ?"
        args.append(client_scope)

    if q:
        sql += """
            AND (
                d.source_doc_id LIKE ?
                OR d.doc_name LIKE ?
                OR p.address LIKE ?
                OR d.status LIKE ?
                OR dt.label LIKE ?
                OR c.name LIKE ?
            )
        """
        like = f"%{q}%"
        args.extend([like] * 6)

    if doc_type:
        sql += " AND dt.key = ?"
        args.append(doc_type)

    if status:
        sql += " AND d.status = ?"
        args.append(status)

    sort_map = {
        "newest": "d.scanned_at DESC, COALESCE(d.batch_date, d.scanned_at, d.reviewed_at) DESC",
        "oldest": "d.scanned_at ASC, COALESCE(d.batch_date, d.scanned_at, d.reviewed_at) ASC",
        "name": "d.doc_name ASC",
        "status": "d.status ASC",
    }
    sql += f" ORDER BY {sort_map.get(sort, sort_map['newest'])}"
    sql += " LIMIT ?"
    args.append(limit)

    docs = query_db(sql, args)

    # Fetch fields for each document
    conn = get_db()
    try:
        for doc in docs:
            cur = conn.execute(
                "SELECT field_key, field_label, field_value FROM document_fields WHERE document_id = ?",
                (doc["id"],),
            )
            doc["fields"] = {
                row["field_key"]: {
                    "label": row["field_label"] or row["field_key"].replace("_", " ").title(),
                    "value": row["field_value"] or "",
                }
                for row in cur.fetchall()
            }
    finally:
        conn.close()

    for doc in docs:
        doc["pdf_url"] = scanstation_pdf_url(doc.get("client_name"), doc.get("source_doc_id"))

    return jsonify({"documents": docs, "count": len(docs)})


@app.route("/api/documents/by-id/<int:doc_id>")
@login_required
def api_document_detail_by_id(doc_id: int):
    """Get a single document by portal documents.id (matches document viewer /document/by-id/...)."""
    doc = query_db(
        """
        SELECT
            d.id,
            d.source_doc_id,
            d.doc_name,
            d.status,
            d.pdf_path,
            d.quality_score,
            d.reviewed_by,
            d.reviewed_at,
            d.scanned_at,
            d.batch_date,
            COALESCE(d.batch_date, d.scanned_at, d.reviewed_at) AS imported_at,
            dt.label AS doc_type,
            dt.key AS doc_type_slug,
            c.name AS client_name,
            p.address AS property_address
        FROM documents d
        LEFT JOIN document_types dt ON d.document_type_id = dt.id
        LEFT JOIN clients c ON d.client_id = c.id
        LEFT JOIN properties p ON d.property_id = p.id
        WHERE d.id = ?
        """,
        (doc_id,),
        one=True,
    )

    if not doc:
        abort(404, description="Document not found")

    client_scope = get_current_client() or ""
    if client_scope and _norm_client_name(doc.get("client_name")) != _norm_client_name(client_scope):
        abort(404, description="Document not found")

    fields = query_db(
        "SELECT field_key, field_label, field_value FROM document_fields WHERE document_id = ?",
        (doc["id"],),
    )
    doc["fields"] = {
        f["field_key"]: {
            "label": f["field_label"] or f["field_key"].replace("_", " ").title(),
            "value": f["field_value"] or "",
        }
        for f in fields
    }

    doc["pdf_url"] = scanstation_pdf_url(doc.get("client_name"), doc.get("source_doc_id"))

    return jsonify(doc)


@app.route("/api/documents/<source_doc_id>")
@login_required
def api_document_detail(source_doc_id):
    """Get a single document by source_doc_id."""
    doc = query_db(
        """
        SELECT
            d.id,
            d.source_doc_id,
            d.doc_name,
            d.status,
            d.pdf_path,
            d.quality_score,
            d.reviewed_by,
            d.reviewed_at,
            d.scanned_at,
            d.batch_date,
            COALESCE(d.batch_date, d.scanned_at, d.reviewed_at) AS imported_at,
            dt.label AS doc_type,
            dt.key AS doc_type_slug,
            c.name AS client_name,
            p.address AS property_address
        FROM documents d
        LEFT JOIN document_types dt ON d.document_type_id = dt.id
        LEFT JOIN clients c ON d.client_id = c.id
        LEFT JOIN properties p ON d.property_id = p.id
        WHERE LOWER(TRIM(d.source_doc_id)) = LOWER(TRIM(?))
        """,
        ((source_doc_id or "").strip(),),
        one=True,
    )

    if not doc:
        abort(404, description="Document not found")

    client_scope = get_current_client() or ""
    if client_scope and _norm_client_name(doc.get("client_name")) != _norm_client_name(client_scope):
        abort(404, description="Document not found")

    fields = query_db(
        "SELECT field_key, field_label, field_value FROM document_fields WHERE document_id = ?",
        (doc["id"],),
    )
    doc["fields"] = {
        f["field_key"]: {
            "label": f["field_label"] or f["field_key"].replace("_", " ").title(),
            "value": f["field_value"] or "",
        }
        for f in fields
    }

    doc["pdf_url"] = scanstation_pdf_url(doc.get("client_name"), doc.get("source_doc_id"))

    return jsonify(doc)


@app.route("/api/documents/by-id/<int:doc_id>/pdf")
@login_required
def serve_document_pdf_by_id(doc_id: int):
    """Same-origin PDF stream for the document viewer (PDF.js); avoids iframe zoom/CORS issues."""
    doc = query_db(
        """
        SELECT
            d.id,
            d.source_doc_id,
            d.pdf_path,
            c.name AS client_name
        FROM documents d
        LEFT JOIN clients c ON d.client_id = c.id
        WHERE d.id = ?
        """,
        (doc_id,),
        one=True,
    )
    if not doc:
        abort(404, description="Document not found")

    client_scope = get_current_client() or ""
    if client_scope and _norm_client_name(doc.get("client_name")) != _norm_client_name(client_scope):
        abort(404, description="Document not found")

    path = _resolve_pdf_path_for_document(doc)
    if not path:
        abort(404, description="PDF not found")

    return send_file(
        path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=os.path.basename(path),
    )


@app.route("/api/documents/by-source/<path:source_doc_id>/pdf")
@login_required
def serve_document_pdf_by_source(source_doc_id: str):
    """Same-origin PDF when only source_doc_id is known (no portal documents.id in URL)."""
    doc = query_db(
        """
        SELECT
            d.id,
            d.source_doc_id,
            d.pdf_path,
            c.name AS client_name
        FROM documents d
        LEFT JOIN clients c ON d.client_id = c.id
        WHERE LOWER(TRIM(d.source_doc_id)) = LOWER(TRIM(?))
        """,
        ((source_doc_id or "").strip(),),
        one=True,
    )
    if not doc:
        abort(404, description="Document not found")

    client_scope = get_current_client() or ""
    if client_scope and _norm_client_name(doc.get("client_name")) != _norm_client_name(client_scope):
        abort(404, description="Document not found")

    path = _resolve_pdf_path_for_document(doc)
    if not path:
        abort(404, description="PDF not found")

    return send_file(
        path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=os.path.basename(path),
    )


ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB
ALLOWED_DOCUMENT_TYPES = {
    "Gas Safety Certificate",
    "EICR",
    "EPC",
    "Deposit Protection Certificate",
    "Tenancy Agreement",
    "Other",
}


@app.route("/api/documents/upload", methods=["POST"])
@login_required
def api_documents_upload():
    """
    Accept a multipart upload: file, property_id, document_type, optional notes.
    Save file to Clients/<ClientName>/raw/ with upload_<timestamp>_<filename>.
    Write .meta.json sidecar for the watcher to auto-classify.
    """
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "Missing file"}), 400

    try:
        property_id = request.form.get("property_id")
        if property_id is None:
            return jsonify({"error": "Missing property_id"}), 400
        property_id = int(property_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid property_id"}), 400

    document_type = (request.form.get("document_type") or "").strip()
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        return jsonify({"error": "Invalid document_type. Must be one of: " + ", ".join(sorted(ALLOWED_DOCUMENT_TYPES))}), 400

    notes = (request.form.get("notes") or "").strip()

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        return jsonify({"error": "Invalid file type. Allowed: .pdf, .jpg, .jpeg, .png, .tiff"}), 400

    # Read and check size (stream would be consumed; we need to save later, so read into memory or save then check)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_UPLOAD_BYTES:
        return jsonify({"error": "File too large. Maximum size is 20MB."}), 400

    # Look up property -> client name and address
    prop = query_db(
        """
        SELECT p.id, p.client_id, p.address AS property_address, c.name AS client_name
        FROM properties p
        JOIN clients c ON p.client_id = c.id
        WHERE p.id = ?
        """,
        (property_id,),
        one=True,
    )
    if not prop:
        return jsonify({"error": "Property not found"}), 404

    client_name = (prop.get("client_name") or "").strip()
    property_address = (prop.get("property_address") or "").strip()
    if not client_name:
        return jsonify({"error": "Property has no client name"}), 400

    raw_dir = os.path.join(get_clients_dir(), client_name, "raw")
    try:
        os.makedirs(raw_dir, exist_ok=True)
    except OSError as e:
        return jsonify({"error": f"Cannot create upload directory: {e}"}), 500

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[<>:"/\\|?*]', "_", file.filename)
    if not safe_name:
        safe_name = "document"
    unique_filename = f"upload_{timestamp}_{safe_name}"
    save_path = os.path.join(raw_dir, unique_filename)

    try:
        file.save(save_path)
    except OSError as e:
        return jsonify({"error": f"Failed to save file: {e}"}), 500

    doc_name = f"{property_address} - {document_type}"
    meta = {
        "doc_name": doc_name,
        "property_address": property_address,
        "doc_type_template": document_type,
    }
    meta_path = save_path + ".meta.json"
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    except OSError as e:
        try:
            os.remove(save_path)
        except OSError:
            pass
        return jsonify({"error": f"Failed to write metadata: {e}"}), 500

    log_activity(
        "document_uploaded",
        entity_type="document",
        entity_id=None,
        description=f"Uploaded {file.filename} for property {property_id}",
        client_id=prop.get("client_id"),
    )
    return jsonify({
        "success": True,
        "message": "Document uploaded. It will appear in your portal within 1-2 minutes after processing.",
    })


@app.route("/api/stats")
@login_required
def api_stats():
    """Dashboard statistics."""
    stats = {
        "total": query_db("SELECT COUNT(*) as n FROM documents", one=True)["n"],
        "verified": query_db(
            "SELECT COUNT(*) as n FROM documents WHERE status = 'verified'", one=True
        )["n"],
        "needs_review": query_db(
            "SELECT COUNT(*) as n FROM documents WHERE status IN ('needs_review', 'new', 'ai_prefilled')",
            one=True,
        )["n"],
        "doc_types": query_db(
            """SELECT dt.label, COUNT(d.id) as count
               FROM documents d
               LEFT JOIN document_types dt ON d.document_type_id = dt.id
               GROUP BY dt.label"""
        ),
        "clients": query_db(
            """SELECT c.name, COUNT(d.id) as count
               FROM documents d
               LEFT JOIN clients c ON d.client_id = c.id
               GROUP BY c.name"""
        ),
    }
    return jsonify(stats)


def _deduplicate_compliance_actions(actions: list[dict]) -> list[dict]:
    """
    Ensure exactly one action per (property_id, comp_type).
    If multiple actions exist for the same property + type (e.g. duplicate raw rows),
    keep the one with the most recent expiry_date so "expired X days ago" reflects
    the latest certificate.
    """
    by_key: dict[tuple[int | None, str], list[dict]] = {}
    for a in actions:
        key = (a.get("property_id"), a.get("type"))
        by_key.setdefault(key, []).append(a)
    out: list[dict] = []
    for key, group in by_key.items():
        if len(group) == 1:
            out.append(group[0])
            continue
        # Pick one: use the action with the latest expiry_date (most recent document).
        best = group[0]
        best_expiry = best.get("expiry_date") or ""
        for a in group[1:]:
            exp = a.get("expiry_date") or ""
            if exp > best_expiry:
                best = a
                best_expiry = exp
        out.append(best)
    return out


@app.route("/api/compliance")
@login_required
def api_compliance():
    """
    Action-oriented compliance snapshot for properties.

    Query params:
        client  - client name filter (optional)

    Returns:
        {
          "stats": { ... },
          "actions": [ ... ],
          "health_by_type": [ ... ]
        }
    """
    client_name = get_current_client() or ""
 
    try:
        raw = compliance_engine.evaluate_compliance()
    except Exception as e:
        # Defensive: never crash the server if compliance evaluation fails.
        return (
            jsonify(
                {
                    "error": "Failed to evaluate compliance",
                    "details": str(e),
                }
            ),
            500,
        )
 
    if client_name:
        raw = [r for r in raw if (r.get("client") or "").strip() == client_name]

    total_properties = len(raw)

    # Resolve client_id for compliance_actions lookups (needed for filtering resolved/snoozed).
    client_id_for_actions = None
    if client_name:
        row = query_db(
            "SELECT id FROM clients WHERE name = ? LIMIT 1",
            (client_name,),
            one=True,
        )
        if row:
            client_id_for_actions = row.get("id")

    TYPES = ["gas_safety", "eicr", "epc", "deposit"]
    TYPE_LABELS = {
        "gas_safety": "Gas safety certificate",
        "eicr": "EICR",
        "epc": "EPC",
        "deposit": "Deposit protection",
    }
    EXPIRED_SEVERITY = {
        "gas_safety": "Landlord liable for £6,000 fine · Property cannot be legally let",
        "eicr": "Landlord liable for up to £30,000 fine",
        "epc": "Required for all rental properties since 2008",
        "deposit": "Tenant may claim up to 3x deposit amount",
    }
    MISSING_SEVERITY = {
        "gas_safety": "Annual inspection required by law for all rental properties",
        "eicr": "Required every 5 years for rental properties since 2020",
        "epc": "Required for all rental properties since 2008",
        "deposit": "Must be protected within 30 days of receipt",
    }
 
    # Build action items and stats.
    actions: list[dict] = []
    counts: dict[str, dict[str, int]] = {
        t: {"valid": 0, "expiring_soon": 0, "expired": 0, "missing": 0} for t in TYPES
    }
    fully_compliant = 0
 
    # Enrich properties with portal property_id for deep links.
    conn = get_db()
    try:
        cur = conn.cursor()
 
        # Cache for expiry lookups (property_id, type) → (expiry_date, days).
        expiry_cache: dict[tuple[int, str], tuple[str | None, int | None]] = {}
 
        def get_property_id(row: dict) -> int | None:
            name = (row.get("client") or "").strip()
            addr = (row.get("property") or "").strip()
            if not name or not addr:
                return None
            res = cur.execute(
                """
                SELECT p.id
                FROM properties p
                JOIN clients c ON p.client_id = c.id
                WHERE c.name = ? AND p.address = ?
                LIMIT 1
                """,
                (name, addr),
            ).fetchone()
            if not res:
                return None
            return res[0]
 
        def get_expiry_for(property_id: int | None, comp_type: str) -> tuple[str | None, int | None]:
            if not property_id:
                return None, None
            key = (property_id, comp_type)
            if key in expiry_cache:
                return expiry_cache[key]
 
            meta = COMPLIANCE_TYPE_META.get(comp_type)
            if not meta:
                expiry_cache[key] = (None, None)
                return None, None
            slug = meta["slug"]
 
            row = cur.execute(
                """
                SELECT d.id
                FROM documents d
                JOIN document_types dt ON d.document_type_id = dt.id
                WHERE d.property_id = ?
                  AND dt.key = ?
                ORDER BY COALESCE(d.batch_date, d.scanned_at, d.reviewed_at) DESC
                LIMIT 1
                """,
                (property_id, slug),
            ).fetchone()
            if not row:
                expiry_cache[key] = (None, None)
                return None, None
 
            doc_id = row[0]
            field_rows = cur.execute(
                "SELECT field_key, field_value FROM document_fields WHERE document_id = ?",
                (doc_id,),
            ).fetchall()
            flat_fields = {
                fr[0]: (fr[1] or "").strip()
                for fr in field_rows
            }
            _, expiry_iso, days = get_compliance_status_for_doc(slug, flat_fields)
            expiry_cache[key] = (expiry_iso, days)
            return expiry_iso, days
 
        for row in raw:
            prop_compliant = True
            property_name = row.get("property", "Unknown")
            client = row.get("client", "")
            property_id = get_property_id(row)
 
            for comp_type in TYPES:
                status = (row.get(comp_type) or "missing").strip()
                if status not in counts[comp_type]:
                    counts[comp_type][status] = 0
                counts[comp_type][status] += 1
 
                if status != "valid":
                    prop_compliant = False
 
                if status in ("expired", "expiring_soon", "missing"):
                    expiry_date, days = get_expiry_for(property_id, comp_type)
 
                    action: dict = {
                        "type": comp_type,
                        "type_label": TYPE_LABELS[comp_type],
                        "status": status,
                        "property": property_name,
                        "property_id": property_id,
                        "client": client,
                        "expiry_date": expiry_date,
                        "days": days,
                    }
 
                    if status == "expired":
                        if days is not None:
                            text = f"Expired {abs(days)} days ago"
                            if expiry_date:
                                text += f" · Was due {expiry_date}"
                            action["display_text"] = text
                            action["badge_text"] = f"{abs(days)} days overdue"
                        else:
                            action["display_text"] = "Expired"
                            action["badge_text"] = "Overdue"
                        action["severity"] = EXPIRED_SEVERITY.get(comp_type, "")
                        action["sort_order"] = 0
                        action["sort_days"] = days if days is not None else -9999
                    elif status == "expiring_soon":
                        if days is not None:
                            text = f"Expires in {days} days"
                            if expiry_date:
                                text += f" · Due {expiry_date}"
                            action["display_text"] = text
                            action["badge_text"] = f"{days} days left"
                        else:
                            action["display_text"] = "Expiring soon"
                            action["badge_text"] = "Expiring"
                        action["severity"] = "Schedule renewal before expiry"
                        action["sort_order"] = 1
                        action["sort_days"] = days if days is not None else 0
                    elif status == "missing":
                        action["display_text"] = "No certificate on file"
                        action["badge_text"] = "Missing"
                        action["severity"] = MISSING_SEVERITY.get(comp_type, "")
                        action["sort_order"] = 2
                        action["sort_days"] = 9999
 
                    actions.append(action)

            if prop_compliant:
                fully_compliant += 1
    finally:
        conn.close()

    # One action per (property_id, comp_type); use most recent expiry when deduplicating.
    actions = _deduplicate_compliance_actions(actions)

    # Cross-reference compliance_actions: exclude resolved, mark snoozed, build resolved list.
    resolved_set = set()
    snoozed_map = {}
    resolved_list: list[dict] = []
    today_iso = date.today().isoformat()
    TYPE_LABELS_REF = {
        "gas_safety": "Gas safety certificate",
        "eicr": "EICR",
        "epc": "EPC",
        "deposit": "Deposit protection",
    }
    if client_id_for_actions is not None:
        conn_act = get_db()
        try:
            cur_act = conn_act.cursor()
            cur_act.execute(
                """
                SELECT property_id, comp_type, status, snoozed_until, resolved_at, resolved_by, notes
                FROM compliance_actions
                WHERE client_id = ?
                """,
                (client_id_for_actions,),
            )
            for r in cur_act.fetchall():
                pid = r[0] if isinstance(r, (tuple, list)) else r["property_id"]
                ctype = r[1] if isinstance(r, (tuple, list)) else r["comp_type"]
                st = r[2] if isinstance(r, (tuple, list)) else r["status"]
                snoozed_until = r[3] if isinstance(r, (tuple, list)) else r["snoozed_until"]
                resolved_at = r[4] if isinstance(r, (tuple, list)) else r["resolved_at"]
                resolved_by = r[5] if isinstance(r, (tuple, list)) else r["resolved_by"]
                notes = r[6] if isinstance(r, (tuple, list)) else r["notes"]
                if st == "resolved":
                    resolved_set.add((pid, ctype))
                    # Resolved list for "Show resolved" section (need property address).
                    addr_row = cur_act.execute(
                        "SELECT address FROM properties WHERE id = ?",
                        (pid,),
                    ).fetchone()
                    prop_addr = (addr_row[0] if addr_row and isinstance(addr_row, (tuple, list)) else (addr_row["address"] if addr_row else "")) or "Unknown"
                    resolved_list.append({
                        "property_id": pid,
                        "property": prop_addr,
                        "comp_type": ctype,
                        "type_label": TYPE_LABELS_REF.get(ctype, ctype),
                        "resolved_at": resolved_at,
                        "resolved_by": resolved_by or "",
                        "notes": notes or "",
                    })
                elif st == "snoozed" and snoozed_until and snoozed_until > today_iso:
                    snoozed_map[(pid, ctype)] = {
                        "until": snoozed_until,
                        "notes": (notes or "").strip(),
                    }
        finally:
            conn_act.close()

    # Exclude resolved actions from main list.
    actions = [a for a in actions if (a.get("property_id"), a.get("type")) not in resolved_set]

    # Mark snoozed and sort snoozed to end.
    for a in actions:
        key = (a.get("property_id"), a.get("type"))
        if key in snoozed_map:
            info = snoozed_map[key]
            a["snoozed"] = True
            a["snoozed_until"] = info["until"]
            if info.get("notes"):
                a["snooze_notes"] = info["notes"]
    actions.sort(key=lambda a: ((1 if a.get("snoozed") else 0), a["sort_order"], a["sort_days"]))

    # Build health_by_type summary.
    health_by_type: list[dict] = []
    for comp_type in TYPES:
        c = counts[comp_type]
        total_checks = sum(c.values())
        has_cert = c.get("valid", 0) + c.get("expiring_soon", 0) + c.get("expired", 0)
        coverage_pct = round((has_cert / total_checks * 100) if total_checks > 0 else 0)
        valid_pct = round((c.get("valid", 0) / total_checks * 100) if total_checks > 0 else 0)
        expired_pct = round((c.get("expired", 0) / total_checks * 100) if total_checks > 0 else 0)
        expiring_pct = round((c.get("expiring_soon", 0) / total_checks * 100) if total_checks > 0 else 0)
        missing_pct = round((c.get("missing", 0) / total_checks * 100) if total_checks > 0 else 0)
 
        health_by_type.append(
            {
                "type": comp_type,
                "label": TYPE_LABELS[comp_type],
                "valid": c.get("valid", 0),
                "expiring_soon": c.get("expiring_soon", 0),
                "expired": c.get("expired", 0),
                "missing": c.get("missing", 0),
                "coverage_pct": coverage_pct,
                "valid_pct": valid_pct,
                "expired_pct": expired_pct,
                "expiring_pct": expiring_pct,
                "missing_pct": missing_pct,
                "total": total_checks,
            }
        )
 
    total_expired = sum(c.get("expired", 0) for c in counts.values())
    total_expiring = sum(c.get("expiring_soon", 0) for c in counts.values())
    total_missing = sum(c.get("missing", 0) for c in counts.values())
 
    resolved_count = len(resolved_list)
    stats = {
        "overdue_actions": total_expired,
        "expiring_soon": total_expiring,
        "missing_certificates": total_missing,
        "fully_compliant": fully_compliant,
        "total_properties": total_properties,
        "resolved_count": resolved_count,
        "overdue_subtitle": "Expired certificates needing immediate attention",
        "expiring_subtitle": "Renewals to schedule this month",
        "missing_subtitle": f"Across {total_properties} properties",
        "compliant_subtitle": f"{fully_compliant} of {total_properties} properties with all certs valid",
    }

    return jsonify({
        "stats": stats,
        "actions": actions,
        "resolved_actions": resolved_list,
        "health_by_type": health_by_type,
    })


def _build_compliance_report_data(client_name: str):
    """
    Build property_rows, actions, and stats for the compliance PDF report.
    Reuses compliance_engine + same action-building and filtering as api_compliance.
    Returns (property_rows, actions, stats) or (None, None, None) on error.
    """
    try:
        raw = compliance_engine.evaluate_compliance()
    except Exception:
        return None, None, None
    if client_name:
        raw = [r for r in raw if (r.get("client") or "").strip() == client_name]
    total_properties = len(raw)
    client_id_for_actions = None
    if client_name:
        row = query_db("SELECT id FROM clients WHERE name = ? LIMIT 1", (client_name,), one=True)
        if row:
            client_id_for_actions = row.get("id")

    TYPES = ["gas_safety", "eicr", "epc", "deposit"]
    TYPE_LABELS = {
        "gas_safety": "Gas safety certificate",
        "eicr": "EICR",
        "epc": "EPC",
        "deposit": "Deposit protection",
    }
    EXPIRED_SEVERITY = {
        "gas_safety": "Landlord liable for £6,000 fine · Property cannot be legally let",
        "eicr": "Landlord liable for up to £30,000 fine",
        "epc": "Required for all rental properties since 2008",
        "deposit": "Tenant may claim up to 3x deposit amount",
    }
    MISSING_SEVERITY = {
        "gas_safety": "Annual inspection required by law for all rental properties",
        "eicr": "Required every 5 years for rental properties since 2020",
        "epc": "Required for all rental properties since 2008",
        "deposit": "Must be protected within 30 days of receipt",
    }

    property_rows: list[dict] = []
    actions: list[dict] = []
    counts: dict[str, dict[str, int]] = {t: {"valid": 0, "expiring_soon": 0, "expired": 0, "missing": 0} for t in TYPES}
    fully_compliant = 0

    conn = get_db()
    try:
        cur = conn.cursor()
        expiry_cache: dict[tuple[int, str], tuple[str | None, int | None]] = {}

        def get_property_id(row: dict) -> int | None:
            name = (row.get("client") or "").strip()
            addr = (row.get("property") or "").strip()
            if not name or not addr:
                return None
            res = cur.execute(
                "SELECT p.id FROM properties p JOIN clients c ON p.client_id = c.id WHERE c.name = ? AND p.address = ? LIMIT 1",
                (name, addr),
            ).fetchone()
            return res[0] if res else None

        def get_expiry_for(property_id: int | None, comp_type: str) -> tuple[str | None, int | None]:
            if not property_id:
                return None, None
            key = (property_id, comp_type)
            if key in expiry_cache:
                return expiry_cache[key]
            meta = COMPLIANCE_TYPE_META.get(comp_type)
            if not meta:
                expiry_cache[key] = (None, None)
                return None, None
            slug = meta["slug"]
            row = cur.execute(
                """SELECT d.id FROM documents d JOIN document_types dt ON d.document_type_id = dt.id
                   WHERE d.property_id = ? AND dt.key = ? ORDER BY COALESCE(d.batch_date, d.scanned_at, d.reviewed_at) DESC LIMIT 1""",
                (property_id, slug),
            ).fetchone()
            if not row:
                expiry_cache[key] = (None, None)
                return None, None
            doc_id = row[0]
            field_rows = cur.execute("SELECT field_key, field_value FROM document_fields WHERE document_id = ?", (doc_id,)).fetchall()
            flat_fields = {fr[0]: (fr[1] or "").strip() for fr in field_rows}
            _, expiry_iso, days = get_compliance_status_for_doc(slug, flat_fields)
            expiry_cache[key] = (expiry_iso, days)
            return expiry_iso, days

        for row in raw:
            prop_compliant = True
            property_name = row.get("property", "Unknown")
            client = row.get("client", "")
            property_id = get_property_id(row)
            pr: dict = {
                "address": property_name,
                "property_id": property_id,
                "gas_safety": {},
                "eicr": {},
                "epc": {},
                "deposit": {},
            }
            for comp_type in TYPES:
                status = (row.get(comp_type) or "missing").strip()
                if status not in counts[comp_type]:
                    counts[comp_type][status] = 0
                counts[comp_type][status] += 1
                if status != "valid":
                    prop_compliant = False
                expiry_date, days = get_expiry_for(property_id, comp_type)
                pr[comp_type] = {"status": status, "expiry_date": expiry_date or "", "days": days}
                if status in ("expired", "expiring_soon", "missing"):
                    action = {
                        "type": comp_type,
                        "type_label": TYPE_LABELS[comp_type],
                        "status": status,
                        "property": property_name,
                        "property_id": property_id,
                        "expiry_date": expiry_date,
                        "days": days,
                        "sort_order": 0 if status == "expired" else (1 if status == "expiring_soon" else 2),
                        "sort_days": days if days is not None else (9999 if status == "missing" else -9999),
                    }
                    if status == "expired":
                        action["badge_text"] = f"{abs(days)} days overdue" if days is not None else "Overdue"
                        action["severity"] = EXPIRED_SEVERITY.get(comp_type, "")
                    elif status == "expiring_soon":
                        action["badge_text"] = f"{days} days left" if days is not None else "Expiring"
                        action["severity"] = "Schedule renewal before expiry"
                    else:
                        action["badge_text"] = "Missing"
                        action["severity"] = MISSING_SEVERITY.get(comp_type, "")
                    actions.append(action)
            property_rows.append(pr)
            if prop_compliant:
                fully_compliant += 1
    finally:
        conn.close()

    # One action per (property_id, comp_type); use most recent expiry when deduplicating.
    actions = _deduplicate_compliance_actions(actions)

    # Filter by compliance_actions (resolved / snoozed)
    resolved_set = set()
    snoozed_map = {}
    today_iso = date.today().isoformat()
    if client_id_for_actions is not None:
        conn_act = get_db()
        try:
            cur_act = conn_act.cursor()
            cur_act.execute(
                "SELECT property_id, comp_type, status, snoozed_until FROM compliance_actions WHERE client_id = ?",
                (client_id_for_actions,),
            )
            for r in cur_act.fetchall():
                pid = r[0] if isinstance(r, (tuple, list)) else r["property_id"]
                ctype = r[1] if isinstance(r, (tuple, list)) else r["comp_type"]
                st = r[2] if isinstance(r, (tuple, list)) else r["status"]
                snoozed_until = r[3] if isinstance(r, (tuple, list)) else r["snoozed_until"]
                if st == "resolved":
                    resolved_set.add((pid, ctype))
                elif st == "snoozed" and snoozed_until and snoozed_until > today_iso:
                    snoozed_map[(pid, ctype)] = snoozed_until
        finally:
            conn_act.close()
    actions = [a for a in actions if (a.get("property_id"), a.get("type")) not in resolved_set]
    for a in actions:
        key = (a.get("property_id"), a.get("type"))
        if key in snoozed_map:
            a["snoozed"] = True
    actions.sort(key=lambda a: (a.get("snoozed", False), a["sort_order"], a["sort_days"]))

    total_expired = sum(c.get("expired", 0) for c in counts.values())
    total_expiring = sum(c.get("expiring_soon", 0) for c in counts.values())
    total_missing = sum(c.get("missing", 0) for c in counts.values())
    stats = {
        "total_properties": total_properties,
        "fully_compliant": fully_compliant,
        "overdue_actions": total_expired,
        "expiring_soon": total_expiring,
        "missing_certificates": total_missing,
    }
    return property_rows, actions, stats


def _generate_compliance_pdf(client_name: str, property_rows: list, actions: list, stats: dict) -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=20 * mm, bottomMargin=22 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name="ReportTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    heading_style = ParagraphStyle(name="ReportHeading", parent=styles["Heading2"], fontSize=12, spaceAfter=6)
    normal = styles["Normal"]
    footer_text = "Generated %s by MorphIQ — Not just scanned, understood." % date.today().strftime("%d %b %Y")

    story = []
    story.append(Paragraph("MorphIQ Compliance Report", title_style))
    story.append(Paragraph(f"Client: {client_name or 'All clients'}", normal))
    story.append(Paragraph(f"Date generated: {date.today().strftime('%d %B %Y')}", normal))
    story.append(Paragraph("Prepared by MorphIQ — morphiq.co.uk", normal))
    story.append(Spacer(1, 8 * mm))

    # Portfolio summary
    story.append(Paragraph("Portfolio summary", heading_style))
    total = stats.get("total_properties", 0)
    compliant = stats.get("fully_compliant", 0)
    pct = round((compliant / total * 100) if total else 0)
    summary_data = [
        ["Total properties", str(total)],
        ["Fully compliant", f"{compliant} ({pct}%)"],
        ["Expiring soon", str(stats.get("expiring_soon", 0))],
        ["Expired", str(stats.get("overdue_actions", 0))],
        ["Missing", str(stats.get("missing_certificates", 0))],
    ]
    t = Table(summary_data, colWidths=[80 * mm, 40 * mm])
    t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 10)]))
    story.append(t)
    story.append(Spacer(1, 10 * mm))

    # Per-property table
    story.append(Paragraph("Per-property compliance", heading_style))
    green = colors.HexColor("#22c55e")
    amber = colors.HexColor("#f59e0b")
    red = colors.HexColor("#ef4444")
    grey = colors.HexColor("#6b7280")

    headers = ["Property", "Gas Safety", "EICR", "EPC", "Deposit"]
    table_data = [headers]
    for pr in property_rows:
        def fmt(t: str):
            d = pr.get(t, {})
            st = (d.get("status") or "").strip()
            exp = d.get("expiry_date") or ""
            days = d.get("days")
            if st == "valid":
                return exp or "Valid"
            if st == "expiring_soon":
                return f"{exp} ({days}d)" if exp else "Expiring"
            if st == "expired":
                return f"{exp} ({abs(days or 0)}d overdue)" if exp else "Overdue"
            return "Missing"
        table_data.append([
            (pr.get("address") or "")[:40],
            fmt("gas_safety"),
            fmt("eicr"),
            fmt("epc"),
            fmt("deposit"),
        ])
    col_widths = [55 * mm, 28 * mm, 28 * mm, 28 * mm, 28 * mm]
    t2 = Table(table_data, colWidths=col_widths, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a3b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#374151")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#0d2526"), colors.HexColor("#061617")]),
    ]
    for i, pr in enumerate(property_rows):
        row_idx = i + 1
        for col, comp_type in enumerate(["gas_safety", "eicr", "epc", "deposit"], start=1):
            st = (pr.get(comp_type) or {}).get("status") or "missing"
            if st == "valid":
                style.append(("TEXTCOLOR", (col, row_idx), (col, row_idx), green))
            elif st == "expiring_soon":
                style.append(("TEXTCOLOR", (col, row_idx), (col, row_idx), amber))
            elif st == "expired":
                style.append(("TEXTCOLOR", (col, row_idx), (col, row_idx), red))
            else:
                style.append(("TEXTCOLOR", (col, row_idx), (col, row_idx), grey))
    t2.setStyle(TableStyle(style))
    story.append(t2)
    story.append(Spacer(1, 10 * mm))

    # Actions section
    story.append(Paragraph("Actions required", heading_style))
    if not actions:
        story.append(Paragraph("No expired, expiring or missing items.", normal))
    else:
        act_data = [["Property", "Type", "Status", "Severity"]]
        for a in actions:
            if a.get("snoozed"):
                continue
            act_data.append([
                (a.get("property") or "")[:35],
                a.get("type_label") or a.get("type", ""),
                a.get("badge_text") or "",
                (a.get("severity") or "")[:50],
            ])
        if len(act_data) > 1:
            t3 = Table(act_data, colWidths=[50 * mm, 35 * mm, 30 * mm, 50 * mm], repeatRows=1)
            t3.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a3b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#374151")),
            ]))
            story.append(t3)
        else:
            story.append(Paragraph("No outstanding actions.", normal))

    doc.build(story, onFirstPage=lambda canvas, doc: canvas.drawString(20 * mm, 15 * mm, footer_text), onLaterPages=lambda canvas, doc: canvas.drawString(20 * mm, 15 * mm, footer_text))
    buf.seek(0)
    return buf


@app.route("/api/compliance/report")
@login_required
def api_compliance_report():
    """GET ?client=X&format=pdf — generate compliance report PDF."""
    client_name = (request.args.get("client") or "").strip() or (get_current_client() or "")
    if not client_name:
        return jsonify({"error": "Client name required"}), 400
    fmt = (request.args.get("format") or "").strip().lower()
    if fmt != "pdf":
        return jsonify({"error": "format=pdf required"}), 400
    property_rows, actions, stats = _build_compliance_report_data(client_name)
    if property_rows is None:
        return jsonify({"error": "Failed to build compliance data"}), 500
    buf = _generate_compliance_pdf(client_name, property_rows, actions, stats)
    safe_name = re.sub(r"[^\w\s-]", "", client_name).strip()[:50] or "Client"
    filename = f"MorphIQ_Compliance_Report_{safe_name}_{date.today().isoformat()}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=filename)


@app.route("/api/compliance/actions/resolve", methods=["POST"])
@login_required
def api_compliance_resolve():
    """
    Mark a compliance action as resolved.
    Body: { "property_id": int, "comp_type": "gas_safety"|"eicr"|"epc"|"deposit", "notes": "..." }
    """
    payload = request.get_json(silent=True) or {}
    property_id = payload.get("property_id")
    comp_type = (payload.get("comp_type") or "").strip()
    notes = (payload.get("notes") or "").strip()

    if property_id is None or not comp_type:
        return jsonify({"error": "Missing property_id or comp_type"}), 400
    try:
        property_id = int(property_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid property_id"}), 400
    if comp_type not in ("gas_safety", "eicr", "epc", "deposit"):
        return jsonify({"error": "Invalid comp_type"}), 400

    conn = get_db()
    try:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT client_id FROM properties WHERE id = ?",
            (property_id,),
        ).fetchone()
        if not row:
            return jsonify({"error": "Property not found"}), 404
        client_id = row[0] if isinstance(row, (tuple, list)) else row["client_id"]

        now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        resolved_by = getattr(current_user, "full_name", None) or ""

        cur.execute(
            """
            INSERT INTO compliance_actions
            (client_id, property_id, comp_type, status, resolved_at, resolved_by, notes, created_at)
            VALUES (?, ?, ?, 'resolved', ?, ?, ?, ?)
            ON CONFLICT(client_id, property_id, comp_type) DO UPDATE SET
                status = 'resolved',
                resolved_at = excluded.resolved_at,
                resolved_by = excluded.resolved_by,
                notes = excluded.notes,
                snoozed_until = NULL
            """,
            (client_id, property_id, comp_type, now_iso, resolved_by, notes, now_iso),
        )
        conn.commit()
    finally:
        conn.close()
    rdesc = f"Resolved {comp_type} for property {property_id}"
    if notes:
        rdesc += " — " + (notes[:240] + "…" if len(notes) > 240 else notes)
    log_activity(
        "compliance_resolved",
        entity_type="compliance_action",
        entity_id=property_id,
        description=rdesc,
        client_id=client_id,
    )
    return jsonify({"success": True})


@app.route("/api/compliance/actions/snooze", methods=["POST"])
@login_required
def api_compliance_snooze():
    """
    Snooze a compliance action.
    Body: { "property_id": int, "comp_type": "gas_safety", "days": 7 (1–730), "notes": "optional" }
    """
    payload = request.get_json(silent=True) or {}
    property_id = payload.get("property_id")
    comp_type = (payload.get("comp_type") or "").strip()
    days = payload.get("days", 7)
    notes = (payload.get("notes") or "").strip()

    if property_id is None or not comp_type:
        return jsonify({"error": "Missing property_id or comp_type"}), 400
    try:
        property_id = int(property_id)
        days = int(days)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid property_id or days"}), 400
    if comp_type not in ("gas_safety", "eicr", "epc", "deposit"):
        return jsonify({"error": "Invalid comp_type"}), 400
    if days < 1 or days > 730:
        return jsonify({"error": "days must be between 1 and 730"}), 400

    conn = get_db()
    try:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT client_id FROM properties WHERE id = ?",
            (property_id,),
        ).fetchone()
        if not row:
            return jsonify({"error": "Property not found"}), 404
        client_id = row[0] if isinstance(row, (tuple, list)) else row["client_id"]

        today = date.today()
        snoozed_until = (today + timedelta(days=days)).isoformat()
        now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        cur.execute(
            """
            INSERT INTO compliance_actions
            (client_id, property_id, comp_type, status, snoozed_until, notes, created_at)
            VALUES (?, ?, ?, 'snoozed', ?, ?, ?)
            ON CONFLICT(client_id, property_id, comp_type) DO UPDATE SET
                status = 'snoozed',
                snoozed_until = excluded.snoozed_until,
                resolved_at = NULL,
                resolved_by = NULL,
                notes = excluded.notes
            """,
            (client_id, property_id, comp_type, snoozed_until, notes, now_iso),
        )
        conn.commit()
    finally:
        conn.close()
    desc = f"Snoozed {comp_type} for property {property_id}"
    if notes:
        desc += " — " + (notes[:240] + "…" if len(notes) > 240 else notes)
    log_activity(
        "compliance_snoozed",
        entity_type="compliance_action",
        entity_id=property_id,
        description=desc,
        client_id=client_id,
    )
    return jsonify({"success": True, "snoozed_until": snoozed_until})


@app.route("/api/compliance/actions/resolved", methods=["DELETE"])
@login_required
def api_compliance_clear_resolved():
    """Delete all compliance_actions rows where status='resolved'. Admin only."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM compliance_actions WHERE status = ?", ("resolved",))
        deleted = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    return jsonify({"success": True, "deleted": deleted})


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    """
    Chat endpoint backed by Claude, enriched with portfolio context for a single client.

    Expects JSON body:
        {
          "message": "...",
          "client": "Client Name"
        }
    """
    # Debug logging for incoming chat requests to help diagnose 400 errors.
    try:
        debug_json = request.get_json(silent=True)
    except Exception:
        debug_json = None
    print(
        "CHAT REQUEST:",
        request.content_type,
        debug_json,
        request.data[:500] if request.data else "NO DATA",
    )

    payload = request.get_json(silent=True)
    if payload is None:
        return (
            jsonify(
                {
                    "error": "No JSON body received",
                    "content_type": request.content_type,
                }
            ),
            400,
        )

    message = (payload.get("message") or "").strip()

    # Resolve client: managers use their assigned client from DB; admins use JSON body then query param.
    role = getattr(current_user, "role", None)
    client_id = getattr(current_user, "client_id", None)
    if role == "manager" and client_id:
        client_name = get_current_client()
    else:
        client_name = (payload.get("client") or "").strip() or (request.args.get("client") or "").strip()
        client_name = client_name or None

    if not message:
        return jsonify({"error": "Missing message"}), 400
    if not client_name:
        return jsonify({"error": "Missing client"}), 400

    # 1) Core portfolio aggregates for this client.
    total_properties_row = query_db(
        """
        SELECT COUNT(*) AS n
        FROM properties p
        JOIN clients c ON p.client_id = c.id
        WHERE c.name = ?
        """,
        (client_name,),
        one=True,
    ) or {"n": 0}
    total_properties = total_properties_row.get("n", 0)

    properties_rows = query_db(
        """
        SELECT
            p.id AS property_id,
            p.address AS property_address
        FROM properties p
        JOIN clients c ON p.client_id = c.id
        WHERE c.name = ?
        ORDER BY p.address
        """,
        (client_name,),
    )

    # 2) Compliance statuses per property using the compliance engine.
    try:
        compliance_rows = compliance_engine.evaluate_compliance()
    except Exception:
        compliance_rows = []

    # Map (client, address) -> property_id for expiry lookups and tenant snapshots.
    property_id_by_addr = {
        (client_name, (p.get("property_address") or "").strip()): p.get("property_id")
        for p in properties_rows
    }

    client_compliance = []
    for row in compliance_rows:
        if (row.get("client") or "").strip() != client_name:
            continue
        addr = (row.get("property") or "").strip()
        prop_id = property_id_by_addr.get((client_name, addr))
        client_compliance.append({
            "property_id": prop_id,
            "property_address": addr,
            "gas_safety": row.get("gas_safety"),
            "eicr": row.get("eicr"),
            "epc": row.get("epc"),
            "deposit": row.get("deposit"),
        })

    # 3) Tenant snapshots for all properties, following the _build_tenant_snapshot pattern.
    tenants: list[dict] = []
    conn = get_db()
    try:
        cur = conn.cursor()
        for prop in properties_rows:
            prop_id = prop.get("property_id")
            address = (prop.get("property_address") or "").strip()
            if not prop_id:
                continue

            # Load latest Tenancy Agreement for this property.
            tenancy_docs = cur.execute(
                """
                SELECT
                    d.id,
                    d.batch_date,
                    d.scanned_at,
                    d.reviewed_at
                FROM documents d
                JOIN document_types dt ON d.document_type_id = dt.id
                WHERE d.property_id = ?
                  AND LOWER(dt.key) = 'tenancy-agreement'
                """,
                (prop_id,),
            ).fetchall()

            if not tenancy_docs:
                continue

            def _doc_sort_key(row):
                # Use same ordering as elsewhere: batch_date > scanned_at > reviewed_at
                for field in ("batch_date", "scanned_at", "reviewed_at"):
                    val = row[field] if isinstance(row, sqlite3.Row) else None
                    if val:
                        return val
                return ""

            latest_row = max(tenancy_docs, key=_doc_sort_key)
            latest_id = latest_row["id"] if isinstance(latest_row, sqlite3.Row) else latest_row[0]

            field_rows = cur.execute(
                "SELECT field_key, field_value FROM document_fields WHERE document_id = ?",
                (latest_id,),
            ).fetchall()
            flat_fields = {
                (fr["field_key"] if isinstance(fr, sqlite3.Row) else fr[0]): (fr["field_value"] if isinstance(fr, sqlite3.Row) else fr[1]) or ""
                for fr in field_rows
            }

            name = (flat_fields.get("tenant_full_name") or "").strip()
            start_raw = (flat_fields.get("start_date") or "").strip()
            end_raw = (flat_fields.get("end_date") or "").strip()
            rent = (flat_fields.get("monthly_rent_amount") or "").strip()
            deposit = (flat_fields.get("deposit_amount") or "").strip()

            end_date = _parse_date(end_raw) if end_raw else None
            if end_date:
                today = date.today()
                if end_date >= today:
                    is_current = True
                    status_text = "Active tenancy"
                else:
                    is_current = False
                    status_text = "Tenancy ended"
            else:
                is_current = None
                status_text = "End date unknown"

            tenants.append(
                {
                    "property_address": address,
                    "tenant_full_name": name or None,
                    "rent_amount": rent or None,
                    "deposit_amount": deposit or None,
                    "start_date": start_raw or None,
                    "end_date": end_raw or None,
                    "is_current": is_current,
                    "status_text": status_text,
                }
            )
    finally:
        conn.close()

    # 4) Document counts by type for this client.
    doc_type_counts = query_db(
        """
        SELECT dt.label, COUNT(*) AS count
        FROM documents d
        JOIN document_types dt ON d.document_type_id = dt.id
        JOIN clients c ON d.client_id = c.id
        WHERE c.name = ?
        GROUP BY dt.label
        ORDER BY COUNT(*) DESC
        """,
        (client_name,),
    )

    # 5) Actions list mirroring /api/compliance logic (expired/expiring/missing only).
    TYPES = ["gas_safety", "eicr", "epc", "deposit"]
    TYPE_LABELS = {
        "gas_safety": "Gas safety certificate",
        "eicr": "EICR",
        "epc": "EPC",
        "deposit": "Deposit protection",
    }
    EXPIRED_SEVERITY = {
        "gas_safety": "Landlord liable for £6,000 fine · Property cannot be legally let",
        "eicr": "Landlord liable for up to £30,000 fine",
        "epc": "Required for all rental properties since 2008",
        "deposit": "Tenant may claim up to 3x deposit amount",
    }
    MISSING_SEVERITY = {
        "gas_safety": "Annual inspection required by law for all rental properties",
        "eicr": "Required every 5 years for rental properties since 2020",
        "epc": "Required for all rental properties since 2008",
        "deposit": "Must be protected within 30 days of receipt",
    }

    actions: list[dict] = []

    # Build cache for expiry lookups.
    conn = get_db()
    try:
        cur = conn.cursor()
        expiry_cache: dict[tuple[int, str], tuple[str | None, int | None]] = {}

        def get_expiry_for(property_id: int | None, comp_type: str) -> tuple[str | None, int | None]:
            if not property_id:
                return None, None
            key = (property_id, comp_type)
            if key in expiry_cache:
                return expiry_cache[key]

            meta = COMPLIANCE_TYPE_META.get(comp_type)
            if not meta:
                expiry_cache[key] = (None, None)
                return None, None
            slug = meta["slug"]

            row = cur.execute(
                """
                SELECT d.id
                FROM documents d
                JOIN document_types dt ON d.document_type_id = dt.id
                WHERE d.property_id = ?
                  AND dt.key = ?
                ORDER BY COALESCE(d.batch_date, d.scanned_at, d.reviewed_at) DESC
                LIMIT 1
                """,
                (property_id, slug),
            ).fetchone()
            if not row:
                expiry_cache[key] = (None, None)
                return None, None

            doc_id = row[0]
            field_rows = cur.execute(
                "SELECT field_key, field_value FROM document_fields WHERE document_id = ?",
                (doc_id,),
                ).fetchall()
            flat_fields = {
                fr[0]: (fr[1] or "").strip()
                for fr in field_rows
            }
            _, expiry_iso, days = get_compliance_status_for_doc(slug, flat_fields)
            expiry_cache[key] = (expiry_iso, days)
            return expiry_iso, days

        for row in compliance_rows:
            if (row.get("client") or "").strip() != client_name:
                continue

            property_name = row.get("property", "Unknown")
            prop_key = (client_name, (property_name or "").strip())
            property_id = property_id_by_addr.get(prop_key)

            for comp_type in TYPES:
                status = (row.get(comp_type) or "missing").strip()
                if status not in ("expired", "expiring_soon", "missing"):
                    continue

                expiry_date, days = get_expiry_for(property_id, comp_type)
                action: dict = {
                    "type": comp_type,
                    "type_label": TYPE_LABELS[comp_type],
                    "status": status,
                    "property": property_name,
                    "property_id": property_id,
                    "expiry_date": expiry_date,
                    "days": days,
                }

                if status == "expired":
                    if days is not None:
                        text = f"Expired {abs(days)} days ago"
                        if expiry_date:
                            text += f" · Was due {expiry_date}"
                        action["description"] = text
                    else:
                        action["description"] = "Expired"
                    action["severity"] = EXPIRED_SEVERITY.get(comp_type, "")
                elif status == "expiring_soon":
                    if days is not None:
                        text = f"Expires in {days} days"
                        if expiry_date:
                            text += f" · Due {expiry_date}"
                        action["description"] = text
                    else:
                        action["description"] = "Expiring soon"
                    action["severity"] = "Schedule renewal before expiry"
                elif status == "missing":
                    action["description"] = "No certificate on file"
                    action["severity"] = MISSING_SEVERITY.get(comp_type, "")

                actions.append(action)
    finally:
        conn.close()

    # Sort actions roughly by urgency then days.
    def _action_sort_key(a: dict):
        status = a.get("status")
        days = a.get("days")
        if status == "expired":
            order = 0
        elif status == "expiring_soon":
            order = 1
        else:
            order = 2
        if days is None:
            days_key = 9999
        else:
            days_key = days
        return (order, days_key)

    actions.sort(key=_action_sort_key)

    portfolio_context = {
        "client": client_name,
        "total_properties": total_properties,
        "properties": client_compliance,
        "tenants": tenants,
        "document_counts": doc_type_counts,
        "actions": actions,
    }

    portfolio_text = json.dumps(portfolio_context, indent=2, default=str)

    system_prompt = (
        f"You are the Morph IQ compliance assistant for {client_name}. "
        "You have access to their complete property portfolio data. "
        "Answer questions about compliance status, expiry dates, document details, tenants, and portfolio health. "
        "Be specific — reference actual property addresses, dates, amounts, and certificate details from the data. "
        "Keep answers concise and actionable. If asked about something not in the data, say so. "
        "Format responses in plain text with line breaks — no markdown headers or bullet points. "
        "You may use **bold** for emphasis where helpful. "
        "When you reference a specific property in your response, format it as [[property address|PROPERTY_ID]] where PROPERTY_ID is the numeric property_id from the data. "
        "For example: [[42 Mandarin Drive, Harlow|3]]. "
        "When referencing a specific compliance type for a property, use [[property address > Gas Safety|PROPERTY_ID:gas_safety]]. "
        "Always use the exact property_id numbers provided in the data. Only use this format for properties that exist in the data — never fabricate IDs. "
        "Compliance type suffix should be one of: gas_safety, eicr, epc, deposit."
    )

    user_content = (
        "<portfolio_data>\n"
        f"{portfolio_text}\n"
        "</portfolio_data>\n\n"
        f"User question: {message}"
    )

    client = anthropic.Anthropic()

    try:
        completion = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_content,
                }
            ],
        )
    except Exception:
        return (
            jsonify(
                {
                    "error": "Unable to connect to Morph IQ Intelligence. Please try again."
                }
            ),
            500,
        )

    # Extract the text content from Claude's response.
    response_text_parts = []
    for block in getattr(completion, "content", []) or []:
        if getattr(block, "type", None) == "text":
            response_text_parts.append(getattr(block, "text", "") or "")
    response_text = "".join(response_text_parts).strip() or ""

    return jsonify({"response": response_text})


# ── Run ──────────────────────────────────────────────────────────────────────
with app.app_context():
    try:
        cleanup_stale_clients()
    except Exception as e:
        print(f"Startup cleanup warning: {e}")
    try:
        ensure_compliance_actions_table()
    except Exception as e:
        print(f"Startup compliance_actions table warning: {e}")
    try:
        ensure_activity_log_table()
    except Exception as e:
        print(f"Startup activity_log table warning: {e}")

if __name__ == "__main__":
    print(f"\n  MorphIQ Portal")
    print(f"  Database: {DATABASE_URL}")
    print(f"  Clients:  {get_clients_dir()}")
    print(f"  Open: http://127.0.0.1:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=True)
