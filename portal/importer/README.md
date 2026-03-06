# Filesystem Importer

This importer ingests the existing local document system into the portal database.

## What it reads
- `Batches/<YYYY-MM-DD>/DOC-XXXXX/review.json`
- PDF file in each DOC folder (via `files.pdf` or folder scan)
- Raw image file reference (via `files.raw_image` or folder scan)

## What it writes
- `clients`
- `document_types`
- `properties`
- `tenants` (for tenancy docs with tenant name)
- `documents`
- `document_fields`
- `compliance_records`

## Incremental behavior
- Documents are upserted using unique key `(client_id, source_doc_id)`.
- Document fields are upserted using unique key `(document_id, field_key)`.
- Compliance records are upserted using unique key `(document_id, record_type)`.

## Important constraints
- The importer does **not** move, rename, or delete source files.
- It stores absolute path references to PDFs/images in the database.

## Example run command
```bash
python -m portal.importer.filesystem_importer \
  --client-name "Belvoir Harlow" \
  --client-root "C:/ScanSystem_v2/Clients/Belvoir Harlow" \
  --dsn "postgresql://morph:password@localhost:5432/morphiq"
```

Or with environment variable:
```bash
export DATABASE_URL="postgresql://morph:password@localhost:5432/morphiq"
python -m portal.importer.filesystem_importer \
  --client-name "Belvoir Harlow" \
  --client-root "C:/ScanSystem_v2/Clients/Belvoir Harlow"
```

## Validation checklist
1. Run importer once and verify rows exist in `documents`, `document_fields`, `properties`.
2. Re-run importer and verify counts do not duplicate (upsert behavior).
3. Check a sample imported document has:
   - `source_doc_id` like `DOC-00001`
   - linked property where `property_address` exists
   - tenant link for tenancy agreements with `tenant_full_name`
   - `pdf_path` referencing original DOC folder PDF
4. Verify compliance records are present when date fields exist (`expiry_date`, `next_inspection_date`, `valid_until`, `end_date`).
