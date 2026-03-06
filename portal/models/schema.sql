-- Phase 2 schema definitions for Morph IQ portal
-- PostgreSQL target

CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(120) UNIQUE NOT NULL,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE document_types (
    id SERIAL PRIMARY KEY,
    key VARCHAR(80) UNIQUE NOT NULL,
    label VARCHAR(120) UNIQUE NOT NULL,
    description TEXT,
    has_expiry BOOLEAN NOT NULL DEFAULT FALSE,
    expiry_field_key VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    address VARCHAR(500) NOT NULL,
    postcode VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_properties_client_address UNIQUE (client_id, address)
);

CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    property_id INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    tenancy_start DATE,
    tenancy_end DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenants_client_property_name UNIQUE (client_id, property_id, full_name)
);

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    property_id INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    document_type_id INTEGER REFERENCES document_types(id) ON DELETE SET NULL,
    source_doc_id VARCHAR(20) NOT NULL,
    doc_name VARCHAR(500),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    pdf_path VARCHAR(500),
    raw_image_path VARCHAR(500),
    full_text TEXT,
    full_text_search TSVECTOR,
    quality_score VARCHAR(20),
    reviewed_by VARCHAR(120),
    reviewed_at TIMESTAMPTZ,
    scanned_at TIMESTAMPTZ,
    exported_at TIMESTAMPTZ,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    batch_date DATE,
    CONSTRAINT uq_documents_client_source_doc_id UNIQUE (client_id, source_doc_id),
    CONSTRAINT ck_documents_source_doc_id_format CHECK (source_doc_id ~ '^DOC-[0-9]{5}$')
);

CREATE TABLE document_fields (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    field_key VARCHAR(100) NOT NULL,
    field_label VARCHAR(200),
    field_value TEXT,
    source VARCHAR(50) NOT NULL DEFAULT 'review_json',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_document_fields_document_key UNIQUE (document_id, field_key)
);

CREATE TABLE compliance_records (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    property_id INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    record_type VARCHAR(100) NOT NULL,
    expiry_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'upcoming',
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_compliance_records_doc_type UNIQUE (document_id, record_type)
);

CREATE INDEX idx_properties_client_id ON properties(client_id);
CREATE INDEX idx_documents_client_id ON documents(client_id);
CREATE INDEX idx_documents_property_id ON documents(property_id);
CREATE INDEX idx_documents_document_type_id ON documents(document_type_id);
CREATE INDEX idx_documents_source_doc_id ON documents(source_doc_id);
CREATE INDEX idx_documents_full_text_search ON documents USING GIN(full_text_search);
CREATE INDEX idx_document_fields_document_id ON document_fields(document_id);
CREATE INDEX idx_document_fields_field_key ON document_fields(field_key);
CREATE INDEX idx_compliance_records_client_id ON compliance_records(client_id);
CREATE INDEX idx_compliance_records_expiry_date ON compliance_records(expiry_date);
CREATE INDEX idx_compliance_records_status ON compliance_records(status);
