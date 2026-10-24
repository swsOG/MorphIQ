-- Core MorphIQ portal schema (SQLite).
--
-- The portal creates its workflow tables (issues, packs, activity log, compliance
-- actions, document config) on start-up. These core tables hold clients,
-- properties, documents and users, and must exist first. Apply with:
--
--     python scripts/init_portal_db.py
--
-- Every statement is idempotent, so running it against an existing portal.db
-- adds anything missing and leaves existing data untouched.

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    contact_email TEXT,
    contact_phone TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'manager',
    client_id INTEGER,
    is_active INTEGER DEFAULT 1,
    created_at TEXT,
    last_login TEXT,
    deleted_at TEXT,
    failed_login_count INTEGER DEFAULT 0,
    locked_until TEXT
);

CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    address TEXT NOT NULL,
    postcode TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    UNIQUE (client_id, address),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    property_id INTEGER,
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    tenancy_start TEXT,
    tenancy_end TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    UNIQUE (client_id, property_id, full_name),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS document_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    label TEXT UNIQUE NOT NULL,
    description TEXT,
    has_expiry INTEGER NOT NULL DEFAULT 0,
    expiry_field_key TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    property_id INTEGER,
    document_type_id INTEGER,
    source_doc_id TEXT NOT NULL,
    doc_name TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    pdf_path TEXT,
    raw_image_path TEXT,
    full_text TEXT,
    quality_score TEXT,
    reviewed_by TEXT,
    reviewed_at TEXT,
    scanned_at TEXT,
    exported_at TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    batch_date TEXT,
    deleted_at TEXT,
    UNIQUE (client_id, source_doc_id),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE SET NULL,
    FOREIGN KEY (document_type_id) REFERENCES document_types(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS document_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    field_key TEXT NOT NULL,
    field_label TEXT,
    field_value TEXT,
    source TEXT NOT NULL DEFAULT 'review_json',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    UNIQUE (document_id, field_key),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS compliance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    property_id INTEGER,
    document_id INTEGER NOT NULL,
    record_type TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'upcoming',
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    UNIQUE (document_id, record_type),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE SET NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_properties_client_id ON properties(client_id);
CREATE INDEX IF NOT EXISTS idx_documents_client_id ON documents(client_id);
CREATE INDEX IF NOT EXISTS idx_documents_property_id ON documents(property_id);
CREATE INDEX IF NOT EXISTS idx_documents_document_type_id ON documents(document_type_id);
CREATE INDEX IF NOT EXISTS idx_documents_source_doc_id ON documents(source_doc_id);
CREATE INDEX IF NOT EXISTS idx_document_fields_document_id ON document_fields(document_id);
CREATE INDEX IF NOT EXISTS idx_document_fields_field_key ON document_fields(field_key);
CREATE INDEX IF NOT EXISTS idx_compliance_records_client_id ON compliance_records(client_id);
CREATE INDEX IF NOT EXISTS idx_compliance_records_expiry_date ON compliance_records(expiry_date);
CREATE INDEX IF NOT EXISTS idx_compliance_records_status ON compliance_records(status);
