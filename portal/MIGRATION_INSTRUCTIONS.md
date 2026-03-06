# Migration Instructions (Phase 2)

Phase 2 adds SQLAlchemy models and a SQL schema definition file but does not add migration files yet.

## 1) Install dependencies

```bash
pip install flask flask-sqlalchemy flask-migrate psycopg2-binary
```

## 2) Configure environment

Set your portal database URL (PostgreSQL):

```bash
export DATABASE_URL="postgresql://<user>:<password>@<host>:5432/<db_name>"
```

## 3) Apply schema manually (temporary Phase 2 path)

Use the generated SQL schema file:

```bash
psql "$DATABASE_URL" -f portal/models/schema.sql
```

## 4) Verify core tables

```bash
psql "$DATABASE_URL" -c "\dt"
```

Expected key tables:
- clients
- properties
- tenants
- documents
- document_fields
- compliance_records
- document_types

## 5) Planned next step (Phase 3+)

When app configuration is in place, switch to migration-based management:

```bash
flask db init
flask db migrate -m "create portal phase2 schema"
flask db upgrade
```

Do this only after finalising the app factory and migration wiring.
