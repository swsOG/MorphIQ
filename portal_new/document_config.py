import json
import os
import sqlite3
from typing import Any


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL", os.path.join(BASE_DIR, "..", "portal.db"))


DEFAULT_DOCUMENT_CONFIGS: list[dict[str, Any]] = [
    {
        "key": "gas-safety-certificate",
        "label": "Gas Safety Certificate",
        "is_active": True,
        "show_in_dashboard": True,
        "show_in_upload": True,
        "show_in_detection": True,
        "display_order": 10,
        "extraction_fields": [
            ("property_address", "Property Address", True),
            ("engineer_name", "Engineer Name", True),
            ("gas_safe_reg", "Gas Safe Registration", True),
            ("inspection_date", "Inspection Date", True),
            ("expiry_date", "Expiry Date", True),
            ("appliances_tested", "Appliances Tested", False),
            ("result", "Result", True),
        ],
        "compliance_rules": [
            {
                "rule_name": "gas_safety",
                "display_label": "Gas Safety Certificate",
                "mandatory": True,
                "track_expiry": True,
                "expiry_field_key": "expiry_date",
                "expiry_field_candidates": ["expiry_date", "next_inspection_date"],
                "expiry_warning_days": 30,
                "rule_order": 10,
                "is_active": True,
            }
        ],
    },
    {
        "key": "eicr",
        "label": "EICR",
        "is_active": True,
        "show_in_dashboard": True,
        "show_in_upload": True,
        "show_in_detection": True,
        "display_order": 20,
        "extraction_fields": [
            ("property_address", "Property Address", True),
            ("electrician_name", "Electrician Name", True),
            ("company_name", "Company Name", False),
            ("registration_number", "Registration Number", False),
            ("inspection_date", "Inspection Date", True),
            ("next_inspection_date", "Next Inspection Date", True),
            ("overall_result", "Overall Result", False),
            ("observations", "Observations", False),
            ("result", "Result", True),
        ],
        "compliance_rules": [
            {
                "rule_name": "eicr",
                "display_label": "EICR",
                "mandatory": True,
                "track_expiry": True,
                "expiry_field_key": "next_inspection_date",
                "expiry_field_candidates": ["next_inspection_date", "expiry_date"],
                "expiry_warning_days": 30,
                "rule_order": 20,
                "is_active": True,
            }
        ],
    },
    {
        "key": "epc",
        "label": "EPC",
        "is_active": True,
        "show_in_dashboard": True,
        "show_in_upload": True,
        "show_in_detection": True,
        "display_order": 30,
        "extraction_fields": [
            ("property_address", "Property Address", True),
            ("epc_rating", "EPC Rating", False),
            ("current_rating", "Current Rating", True),
            ("assessor_name", "Assessor Name", False),
            ("assessment_date", "Assessment Date", True),
            ("expiry_date", "Expiry Date", True),
            ("valid_until", "Valid Until", False),
        ],
        "compliance_rules": [
            {
                "rule_name": "epc",
                "display_label": "EPC",
                "mandatory": True,
                "track_expiry": True,
                "expiry_field_key": "expiry_date",
                "expiry_field_candidates": ["valid_until", "expiry_date"],
                "expiry_warning_days": 30,
                "rule_order": 30,
                "is_active": True,
            }
        ],
    },
    {
        "key": "fire-door-certificate",
        "label": "Fire Door Certificate",
        "is_active": True,
        "show_in_dashboard": True,
        "show_in_upload": True,
        "show_in_detection": True,
        "display_order": 35,
        "extraction_fields": [
            ("property_address", "Property Address", True),
            ("certificate_number", "Certificate Number", True),
            ("door_location", "Door Location", True),
            ("inspection_date", "Inspection Date", True),
            ("result", "Result", True),
            ("next_inspection_date", "Next Inspection Date", False),
        ],
        "compliance_rules": [],
    },
    {
        "key": "deposit-protection-certificate",
        "label": "Deposit Protection Certificate",
        "is_active": True,
        "show_in_dashboard": True,
        "show_in_upload": True,
        "show_in_detection": True,
        "display_order": 40,
        "extraction_fields": [
            ("property_address", "Property Address", True),
            ("tenant_full_name", "Tenant Full Name", False),
            ("tenant_name", "Tenant Name", True),
            ("deposit_amount", "Deposit Amount", True),
            ("scheme_name", "Scheme Name", False),
            ("certificate_number", "Certificate Number", False),
            ("protection_date", "Protection Date", True),
            ("expiry_date", "Expiry Date", False),
            ("valid_until", "Valid Until", False),
        ],
        "compliance_rules": [
            {
                "rule_name": "deposit",
                "display_label": "Deposit Protection Certificate",
                "mandatory": True,
                "track_expiry": True,
                "expiry_field_key": "expiry_date",
                "expiry_field_candidates": ["expiry_date", "valid_until"],
                "expiry_warning_days": 30,
                "rule_order": 40,
                "is_active": True,
            }
        ],
    },
    {
        "key": "tenancy-agreement",
        "label": "Tenancy Agreement",
        "is_active": True,
        "show_in_dashboard": False,
        "show_in_upload": True,
        "show_in_detection": True,
        "display_order": 50,
        "extraction_fields": [
            ("property_address", "Property Address", True),
            ("tenant_full_name", "Tenant Full Name", True),
            ("landlord_name", "Landlord Name", False),
            ("start_date", "Start Date", True),
            ("end_date", "End Date", False),
            ("monthly_rent_amount", "Monthly Rent Amount", True),
            ("deposit_amount", "Deposit Amount", False),
            ("agreement_date", "Agreement Date", False),
        ],
        "compliance_rules": [],
    },
    {
        "key": "inventory",
        "label": "Inventory",
        "is_active": True,
        "show_in_dashboard": False,
        "show_in_upload": True,
        "show_in_detection": True,
        "display_order": 60,
        "extraction_fields": [
            ("property_address", "Property Address", True),
            ("clerk_name", "Clerk Name", False),
            ("inspection_date", "Inspection Date", True),
            ("property_condition_summary", "Property Condition Summary", False),
        ],
        "compliance_rules": [],
    },
    {
        "key": "other",
        "label": "Other",
        "is_active": True,
        "show_in_dashboard": False,
        "show_in_upload": True,
        "show_in_detection": False,
        "display_order": 999,
        "extraction_fields": [],
        "compliance_rules": [],
    },
]


DEFAULT_INACTIVE_KEYS = {"deposit-protection"}


def _connect(database_url: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(database_url or DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _ensure_document_types_columns(conn: sqlite3.Connection) -> None:
    columns = _table_columns(conn, "document_types")
    if "label" not in columns:
        conn.execute("ALTER TABLE document_types ADD COLUMN label TEXT")
    if "is_active" not in columns:
        conn.execute("ALTER TABLE document_types ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    if "has_expiry" not in columns:
        conn.execute("ALTER TABLE document_types ADD COLUMN has_expiry INTEGER NOT NULL DEFAULT 0")
    if "expiry_field_key" not in columns:
        conn.execute("ALTER TABLE document_types ADD COLUMN expiry_field_key TEXT")
    conn.execute("UPDATE document_types SET label = COALESCE(label, key) WHERE label IS NULL OR TRIM(label) = ''")


def ensure_config_tables(conn: sqlite3.Connection) -> None:
    _ensure_document_types_columns(conn)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS extraction_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_type_id INTEGER NOT NULL,
            field_key TEXT NOT NULL,
            field_label TEXT NOT NULL,
            field_order INTEGER NOT NULL DEFAULT 0,
            is_required INTEGER NOT NULL DEFAULT 0,
            include_in_extraction INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1,
            UNIQUE(document_type_id, field_key)
        );

        CREATE TABLE IF NOT EXISTS compliance_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_type_id INTEGER NOT NULL,
            rule_name TEXT NOT NULL,
            display_label TEXT NOT NULL,
            mandatory INTEGER NOT NULL DEFAULT 1,
            track_expiry INTEGER NOT NULL DEFAULT 1,
            expiry_field_key TEXT,
            expiry_field_candidates TEXT,
            expiry_warning_days INTEGER NOT NULL DEFAULT 30,
            rule_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            UNIQUE(document_type_id, rule_name)
        );

        CREATE TABLE IF NOT EXISTS dashboard_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_type_id INTEGER NOT NULL UNIQUE,
            show_in_dashboard INTEGER NOT NULL DEFAULT 1,
            show_in_upload INTEGER NOT NULL DEFAULT 1,
            show_in_detection INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        """
    )
    if "expiry_field_candidates" not in _table_columns(conn, "compliance_rules"):
        conn.execute("ALTER TABLE compliance_rules ADD COLUMN expiry_field_candidates TEXT")


def _coerce_bool(value: Any, default: bool = False) -> int:
    if value is None:
        return 1 if default else 0
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if value else 0
    return 1 if str(value).strip().lower() in {"1", "true", "yes", "on"} else 0


def _normalize_key(value: str) -> str:
    text = (value or "").strip().lower()
    text = text.replace("_", "-")
    text = "-".join(part for part in text.split() if part)
    return text


def _default_config_by_key(document_key: str) -> dict[str, Any] | None:
    normalized = _normalize_key(document_key)
    for config in DEFAULT_DOCUMENT_CONFIGS:
        if config["key"] == normalized:
            return config
    return None


def seed_default_config(conn: sqlite3.Connection) -> None:
    ensure_config_tables(conn)
    for config in DEFAULT_DOCUMENT_CONFIGS:
        row = conn.execute(
            "SELECT id FROM document_types WHERE key = ?",
            (config["key"],),
        ).fetchone()
        if row:
            document_type_id = int(row["id"])
            conn.execute(
                """
                UPDATE document_types
                SET label = ?, is_active = ?, has_expiry = ?, expiry_field_key = ?
                WHERE id = ?
                """,
                (
                    config["label"],
                    _coerce_bool(config.get("is_active"), True),
                    _coerce_bool(bool(config.get("compliance_rules")), False),
                    (config.get("compliance_rules") or [{}])[0].get("expiry_field_key") if config.get("compliance_rules") else None,
                    document_type_id,
                ),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO document_types (key, label, is_active, has_expiry, expiry_field_key)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    config["key"],
                    config["label"],
                    _coerce_bool(config.get("is_active"), True),
                    _coerce_bool(bool(config.get("compliance_rules")), False),
                    (config.get("compliance_rules") or [{}])[0].get("expiry_field_key") if config.get("compliance_rules") else None,
                ),
            )
            document_type_id = int(cur.lastrowid)

        for index, (field_key, field_label, is_required) in enumerate(config.get("extraction_fields") or [], start=1):
            existing_field = conn.execute(
                "SELECT id FROM extraction_fields WHERE document_type_id = ? AND field_key = ?",
                (document_type_id, field_key),
            ).fetchone()
            if existing_field:
                conn.execute(
                    """
                    UPDATE extraction_fields
                    SET field_label = ?, field_order = ?, is_required = ?, include_in_extraction = 1, is_active = 1
                    WHERE id = ?
                    """,
                    (field_label, index, _coerce_bool(is_required, False), int(existing_field["id"])),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO extraction_fields
                        (document_type_id, field_key, field_label, field_order, is_required, include_in_extraction, is_active)
                    VALUES (?, ?, ?, ?, ?, 1, 1)
                    """,
                    (document_type_id, field_key, field_label, index, _coerce_bool(is_required, False)),
                )

        for rule in config.get("compliance_rules") or []:
            existing_rule = conn.execute(
                "SELECT id FROM compliance_rules WHERE document_type_id = ? AND rule_name = ?",
                (document_type_id, rule["rule_name"]),
            ).fetchone()
            rule_values = (
                rule["display_label"],
                _coerce_bool(rule.get("mandatory"), True),
                _coerce_bool(rule.get("track_expiry"), True),
                rule.get("expiry_field_key"),
                json.dumps(rule.get("expiry_field_candidates") or []),
                int(rule.get("expiry_warning_days") or 30),
                int(rule.get("rule_order") or 0),
                _coerce_bool(rule.get("is_active"), True),
            )
            if existing_rule:
                conn.execute(
                    """
                    UPDATE compliance_rules
                    SET display_label = ?, mandatory = ?, track_expiry = ?, expiry_field_key = ?,
                        expiry_field_candidates = ?, expiry_warning_days = ?, rule_order = ?, is_active = ?
                    WHERE id = ?
                    """,
                    (*rule_values, int(existing_rule["id"])),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO compliance_rules
                        (document_type_id, rule_name, display_label, mandatory, track_expiry, expiry_field_key, expiry_field_candidates, expiry_warning_days, rule_order, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (document_type_id, rule["rule_name"], *rule_values),
                )

        existing_dashboard = conn.execute(
            "SELECT id FROM dashboard_config WHERE document_type_id = ?",
            (document_type_id,),
        ).fetchone()
        dashboard_values = (
            _coerce_bool(config.get("show_in_dashboard"), False),
            _coerce_bool(config.get("show_in_upload"), True),
            _coerce_bool(config.get("show_in_detection"), True),
            int(config.get("display_order") or 0),
            _coerce_bool(config.get("is_active"), True),
        )
        if existing_dashboard:
            conn.execute(
                """
                UPDATE dashboard_config
                SET show_in_dashboard = ?, show_in_upload = ?, show_in_detection = ?, display_order = ?, is_active = ?
                WHERE id = ?
                """,
                (*dashboard_values, int(existing_dashboard["id"])),
            )
        else:
            conn.execute(
                """
                INSERT INTO dashboard_config
                    (document_type_id, show_in_dashboard, show_in_upload, show_in_detection, display_order, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (document_type_id, *dashboard_values),
            )

    for legacy_key in DEFAULT_INACTIVE_KEYS:
        conn.execute(
            "UPDATE document_types SET is_active = 0 WHERE key = ?",
            (legacy_key,),
        )


def ensure_document_config(database_url: str | None = None) -> None:
    conn = _connect(database_url)
    try:
        seed_default_config(conn)
        conn.commit()
    finally:
        conn.close()


def _fetch_document_configs(conn: sqlite3.Connection, include_inactive: bool = False) -> list[dict[str, Any]]:
    ensure_config_tables(conn)
    types = conn.execute(
        """
        SELECT
            dt.id,
            dt.key,
            dt.label,
            COALESCE(dt.is_active, 1) AS document_is_active,
            COALESCE(dt.has_expiry, 0) AS has_expiry,
            dt.expiry_field_key,
            COALESCE(dc.show_in_dashboard, 0) AS show_in_dashboard,
            COALESCE(dc.show_in_upload, 1) AS show_in_upload,
            COALESCE(dc.show_in_detection, 1) AS show_in_detection,
            COALESCE(dc.display_order, 0) AS display_order,
            COALESCE(dc.is_active, 1) AS dashboard_is_active
        FROM document_types dt
        LEFT JOIN dashboard_config dc ON dc.document_type_id = dt.id
        ORDER BY COALESCE(dc.display_order, 0), dt.label, dt.key
        """
    ).fetchall()

    field_rows = conn.execute(
        """
        SELECT
            ef.document_type_id,
            ef.field_key,
            ef.field_label,
            ef.field_order,
            COALESCE(ef.is_required, 0) AS is_required,
            COALESCE(ef.include_in_extraction, 1) AS include_in_extraction,
            COALESCE(ef.is_active, 1) AS is_active
        FROM extraction_fields ef
        ORDER BY ef.document_type_id, ef.field_order, ef.id
        """
    ).fetchall()
    fields_by_type: dict[int, list[sqlite3.Row]] = {}
    for row in field_rows:
        fields_by_type.setdefault(int(row["document_type_id"]), []).append(row)

    rule_rows = conn.execute(
        """
        SELECT
            cr.document_type_id,
            cr.rule_name,
            cr.display_label,
            COALESCE(cr.mandatory, 1) AS mandatory,
            COALESCE(cr.track_expiry, 1) AS track_expiry,
            cr.expiry_field_key,
            cr.expiry_field_candidates,
            COALESCE(cr.expiry_warning_days, 30) AS expiry_warning_days,
            COALESCE(cr.rule_order, 0) AS rule_order,
            COALESCE(cr.is_active, 1) AS is_active
        FROM compliance_rules cr
        ORDER BY cr.document_type_id, cr.rule_order, cr.id
        """
    ).fetchall()
    rules_by_type: dict[int, list[sqlite3.Row]] = {}
    for row in rule_rows:
        rules_by_type.setdefault(int(row["document_type_id"]), []).append(row)

    configs: list[dict[str, Any]] = []
    for row in types:
        is_active = bool(row["document_is_active"]) and bool(row["dashboard_is_active"])
        if not include_inactive and not is_active:
            continue
        document_type_id = int(row["id"])
        fields = []
        required_fields = []
        for field in fields_by_type.get(document_type_id, []):
            if not field["is_active"] or not field["include_in_extraction"]:
                continue
            fields.append(
                {
                    "field_key": field["field_key"],
                    "field_label": field["field_label"],
                    "field_order": int(field["field_order"] or 0),
                    "is_required": bool(field["is_required"]),
                }
            )
            if field["is_required"]:
                required_fields.append(field["field_key"])

        rules = []
        for rule in rules_by_type.get(document_type_id, []):
            if not rule["is_active"]:
                continue
            candidates = []
            raw_candidates = rule["expiry_field_candidates"]
            if raw_candidates:
                try:
                    candidates = [value for value in json.loads(raw_candidates) if value]
                except json.JSONDecodeError:
                    candidates = []
            if not candidates and rule["expiry_field_key"]:
                candidates = [rule["expiry_field_key"]]
            default_config = _default_config_by_key(row["key"])
            if not candidates and default_config:
                for default_rule in default_config.get("compliance_rules") or []:
                    if default_rule["rule_name"] == rule["rule_name"]:
                        candidates = list(default_rule.get("expiry_field_candidates") or [])
                        break
            rules.append(
                {
                    "rule_name": rule["rule_name"],
                    "display_label": rule["display_label"],
                    "mandatory": bool(rule["mandatory"]),
                    "track_expiry": bool(rule["track_expiry"]),
                    "expiry_field_key": rule["expiry_field_key"],
                    "expiry_field_candidates": candidates,
                    "expiry_warning_days": int(rule["expiry_warning_days"] or 30),
                    "rule_order": int(rule["rule_order"] or 0),
                }
            )

        configs.append(
            {
                "document_type_id": document_type_id,
                "document_key": row["key"],
                "label": row["label"],
                "is_active": is_active,
                "show_in_dashboard": bool(row["show_in_dashboard"]),
                "show_in_upload": bool(row["show_in_upload"]),
                "show_in_detection": bool(row["show_in_detection"]),
                "display_order": int(row["display_order"] or 0),
                "field_keys": [field["field_key"] for field in fields],
                "required_fields": required_fields,
                "extraction_fields": fields,
                "compliance_rules": rules,
            }
        )
    return configs


def get_document_configs(database_url: str | None = None, include_inactive: bool = False) -> list[dict[str, Any]]:
    ensure_document_config(database_url)
    conn = _connect(database_url)
    try:
        return _fetch_document_configs(conn, include_inactive=include_inactive)
    finally:
        conn.close()


def find_document_config(doc_type: str, database_url: str | None = None, include_inactive: bool = False) -> dict[str, Any] | None:
    normalized = _normalize_key(doc_type)
    label_normalized = (doc_type or "").strip().casefold()
    for config in get_document_configs(database_url, include_inactive=include_inactive):
        if config["document_key"] == normalized:
            return config
        if config["label"].strip().casefold() == label_normalized:
            return config
    return None


def get_detection_document_labels(database_url: str | None = None) -> list[str]:
    return [
        config["label"]
        for config in get_document_configs(database_url)
        if config["show_in_detection"] and config["field_keys"]
    ]


def get_upload_document_labels(database_url: str | None = None) -> list[str]:
    return [
        config["label"]
        for config in get_document_configs(database_url)
        if config["show_in_upload"]
    ]


def get_compliance_rule_map(database_url: str | None = None) -> dict[str, dict[str, Any]]:
    rule_map: dict[str, dict[str, Any]] = {}
    for config in get_document_configs(database_url):
        for rule in config["compliance_rules"]:
            rule_map[rule["rule_name"]] = {
                "name": rule["rule_name"],
                "slug": config["document_key"],
                "label": rule["display_label"] or config["label"],
                "mandatory": rule["mandatory"],
                "track_expiry": rule["track_expiry"],
                "expiry_field_key": rule["expiry_field_key"],
                "expiry_field_candidates": rule["expiry_field_candidates"] or ([rule["expiry_field_key"]] if rule["expiry_field_key"] else []),
                "expiry_warning_days": int(rule["expiry_warning_days"] or 30),
            }
    return rule_map


def save_document_config(payload: dict[str, Any], database_url: str | None = None) -> dict[str, Any]:
    ensure_document_config(database_url)
    conn = _connect(database_url)
    try:
        ensure_config_tables(conn)
        document_type = payload.get("document_type") or {}
        label = (document_type.get("label") or "").strip()
        key = _normalize_key(document_type.get("key") or label)
        if not label or not key:
            raise ValueError("document_type.label and document_type.key are required")

        row = conn.execute("SELECT id FROM document_types WHERE key = ?", (key,)).fetchone()
        if row:
            document_type_id = int(row["id"])
            conn.execute(
                """
                UPDATE document_types
                SET label = ?, is_active = ?
                WHERE id = ?
                """,
                (label, _coerce_bool(document_type.get("is_active"), True), document_type_id),
            )
        else:
            cur = conn.execute(
                "INSERT INTO document_types (key, label, is_active) VALUES (?, ?, ?)",
                (key, label, _coerce_bool(document_type.get("is_active"), True)),
            )
            document_type_id = int(cur.lastrowid)

        conn.execute("DELETE FROM extraction_fields WHERE document_type_id = ?", (document_type_id,))
        for index, field in enumerate(payload.get("extraction_fields") or [], start=1):
            field_key = _normalize_key(field.get("field_key") or "").replace("-", "_")
            field_label = (field.get("field_label") or field_key).strip()
            if not field_key:
                continue
            conn.execute(
                """
                INSERT INTO extraction_fields
                    (document_type_id, field_key, field_label, field_order, is_required, include_in_extraction, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    document_type_id,
                    field_key,
                    field_label,
                    index,
                    _coerce_bool(field.get("is_required"), False),
                    _coerce_bool(field.get("include_in_extraction"), True),
                ),
            )

        conn.execute("DELETE FROM compliance_rules WHERE document_type_id = ?", (document_type_id,))
        compliance_rules = payload.get("compliance_rules") or []
        for index, rule in enumerate(compliance_rules, start=1):
            rule_name = _normalize_key(rule.get("rule_name") or label).replace("-", "_")
            expiry_field_key = (rule.get("expiry_field_key") or "").strip() or None
            expiry_candidates = rule.get("expiry_field_candidates")
            if expiry_candidates is None and expiry_field_key:
                expiry_candidates = [expiry_field_key]
            conn.execute(
                """
                INSERT INTO compliance_rules
                    (document_type_id, rule_name, display_label, mandatory, track_expiry, expiry_field_key, expiry_field_candidates, expiry_warning_days, rule_order, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    document_type_id,
                    rule_name,
                    (rule.get("display_label") or label).strip(),
                    _coerce_bool(rule.get("mandatory"), True),
                    _coerce_bool(rule.get("track_expiry"), bool(expiry_field_key)),
                    expiry_field_key,
                    json.dumps(expiry_candidates or []),
                    int(rule.get("expiry_warning_days") or 30),
                    index,
                ),
            )

        dashboard = payload.get("dashboard") or {}
        existing_dashboard = conn.execute(
            "SELECT id FROM dashboard_config WHERE document_type_id = ?",
            (document_type_id,),
        ).fetchone()
        dashboard_values = (
            _coerce_bool(dashboard.get("show_in_dashboard"), False),
            _coerce_bool(dashboard.get("show_in_upload"), True),
            _coerce_bool(dashboard.get("show_in_detection"), True),
            int(dashboard.get("display_order") or 0),
            _coerce_bool(dashboard.get("is_active"), True),
        )
        if existing_dashboard:
            conn.execute(
                """
                UPDATE dashboard_config
                SET show_in_dashboard = ?, show_in_upload = ?, show_in_detection = ?, display_order = ?, is_active = ?
                WHERE id = ?
                """,
                (*dashboard_values, int(existing_dashboard["id"])),
            )
        else:
            conn.execute(
                """
                INSERT INTO dashboard_config
                    (document_type_id, show_in_dashboard, show_in_upload, show_in_detection, display_order, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (document_type_id, *dashboard_values),
            )

        first_rule = (compliance_rules or [{}])[0]
        conn.execute(
            """
            UPDATE document_types
            SET has_expiry = ?, expiry_field_key = ?
            WHERE id = ?
            """,
            (
                _coerce_bool(bool(compliance_rules), False),
                (first_rule.get("expiry_field_key") or "").strip() or None,
                document_type_id,
            ),
        )

        conn.commit()
        saved = find_document_config(key, database_url, include_inactive=True)
        if saved is None:
            raise RuntimeError("Failed to load saved config")
        return saved
    finally:
        conn.close()
