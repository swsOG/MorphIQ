# BULK IMPORT — Reference Spec

## Goal
One-off Python script to stress-test the system with 1,000 synthetic document images.

## Input
- Folder of 1,000 JPGs named like: `0001_inventory.jpg`, `0002_gas_safety.jpg`, etc.
- Document type is in the filename (after `NNNN_`, before `.jpg`)

## Client Distribution

| Client | Agency Name | Docs | Properties |
|--------|------------|------|------------|
| A | Northgate Properties | 50 | 5 |
| B | Oakwood Lettings | 100 | 10 |
| C | Riverside Property Management | 150 | 15 |
| D | Heritage Estates | 300 | 30 |
| E | Belmont & Associates | 400 | 40 |

## Property Addresses
Generate realistic addresses using Essex/Herts areas: Harlow, Bishops Stortford, Epping, Hoddesdon, Waltham Abbey, Broxbourne, Cheshunt, Sawbridgeworth, Roydon, Nazeing. Postcodes: CM17–CM20, CM23, CM16, EN7–EN11, SG12. Mix of street types (Close, Road, Avenue, Lane, Drive, etc).

## Per Document Pipeline
1. Copy JPG as `original.jpg` into DOC-XXXXX folder
2. ImageMagick processing → `processed.jpg` (same settings as auto-watcher)
3. Tesseract OCR → `ocr_output.txt`
4. AI prefill via `ai_prefill.py` → `ai_prefill.json`
5. Generate `review.json` with status: pending

## Folder Structure
```
ScannedDocuments\[AgencyName]\[PropertyAddress]\DOC-XXXXX\
├── original.jpg
├── processed.jpg
├── ocr_output.txt
├── ai_prefill.json
└── review.json
```

## CLI Flags
- `--source PATH` — input folder of JPGs
- `--client A|B|C|D|E|all` — which client batch to process
- `--cleanup` — remove bulk-imported data (optionally per client)

## Rules
- Reuse existing pipeline components (don't rewrite ImageMagick/OCR/AI logic)
- DOC numbering continues from current highest in ScannedDocuments
- Don't write to portal.db — use existing sync_to_portal.py after
- Add 0.5s delay between API calls for rate limiting
- Log errors and continue, don't abort on single failure
- Log progress: `[3/8] DOC-00053 | gas_safety.jpg → OCR ✓ → AI Prefill ✓`
