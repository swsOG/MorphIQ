"""Deterministic synthetic golden-dataset generator for the eval harness.

Builds 120+ synthetic UK letting-agency documents (PDFs) plus a committed
``manifest.json`` containing, per case, the ground truth and a *recorded*
Gemini-style response with deterministic injected errors. Because the documents
are synthetic we know every correct value, so the recordings are derived from
ground truth and perturbed by seeded noise — this keeps offline CI fully
deterministic while producing realistic (non-perfect) metrics that exercise the
threshold gates.

The PDFs are gitignored and rebuilt on demand; the manifest is committed.

Field schemas (which keys exist per type, which are required) are read from
``portal_new.document_config`` so this generator never duplicates that config.

Usage:
    python eval/golden/generate_golden.py [--out manifest.json]

Expanding the dataset: bump CASES_PER_TYPE or add entries to EDGE_LAYOUT /
OTHER_COUNT, then re-run and commit the regenerated manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

# Make the project root importable when run as a script.
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter  # noqa: E402

from eval import config  # noqa: E402

# --------------------------------------------------------------------------
# Reuse font / text-wrapping helpers from the existing test-doc generator.
# --------------------------------------------------------------------------


def _load_renderer_helpers():
    path = PROJECT_ROOT / "scripts" / "generate_test_documents.py"
    spec = importlib.util.spec_from_file_location("morphiq_doc_renderer", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


_renderer = _load_renderer_helpers()
load_font = _renderer.load_font
wrap_text = _renderer.wrap_text
text_width = _renderer.text_width

# --------------------------------------------------------------------------
# Canvas (150 dpi A4 — smaller files than the 300 dpi capture generator).
# --------------------------------------------------------------------------

W, H = 1240, 1754
MARGIN = 90
TITLE_SIZE = 46
HEADER_SIZE = 30
LABEL_SIZE = 26
VALUE_SIZE = 26
LINE_LEAD = 40

# --------------------------------------------------------------------------
# Dataset shape
# --------------------------------------------------------------------------

CASES_PER_TYPE = 21  # >= 20 per type as required
OTHER_COUNT = 6

# Per-type case layout: index (1-based) -> edge case (None == happy path).
EDGE_LAYOUT: dict[int, str | None] = {
    14: "detection_error",
    15: "poor_ocr",
    16: "rotated",
    17: "multi_page",
    18: "missing_fields",
    19: "missing_fields",
    20: "poor_ocr",
}

# Stable type-key -> canonical label (must match document_config labels).
TYPE_SLUGS = {
    "Gas Safety Certificate": "gas_safety",
    "EICR": "eicr",
    "EPC": "epc",
    "Deposit Protection Certificate": "deposit",
    "Tenancy Agreement": "tenancy",
    "Inventory": "inventory",
}

# --------------------------------------------------------------------------
# Synthetic value pools (no PII — fictional towns/people/companies)
# --------------------------------------------------------------------------

STREETS = ["Example Street", "Demo Avenue", "Fixture Road", "Placeholder Drive",
           "Synthetic Lane", "Sample Way", "Mock Crescent", "Testing Close"]
TOWNS = ["Sampletown", "Mockford", "Testham", "Demochester", "Fakeham", "Stubton"]
FIRST = ["James", "Claire", "Mohammed", "Sandra", "Kevin", "Priya", "George",
         "Irene", "Hannah", "Omar", "Grace", "Liam", "Aisha", "Tomasz"]
LAST = ["Whitfield", "Al-Rashid", "Obi", "Nair", "Kowalski", "Patel", "Okafor",
        "Brennan", "Andersen", "Nowak", "Clarke", "Bennett", "Foster", "Hendry"]
COMPANIES = ["Bright Spark Ltd", "Voltex Electrical", "SafeGas Essex", "Premier Gas",
             "EcoAssess UK", "HomeSurvey Ltd", "County Electrics", "AllGas UK",
             "GreenRate Surveys", "PowerCheck Ltd"]
SCHEMES = ["TDS (Tenancy Deposit Scheme)", "MyDeposits", "DPS (Deposit Protection Service)"]
RESULTS = ["PASS", "SATISFACTORY", "Pass"]
DOOR_LOCATIONS = ["Front entrance", "Communal hallway", "Flat 2 entrance", "Stairwell door"]
AMOUNTS = [950, 1050, 1100, 1200, 1295, 1375, 1400, 1500]
RATINGS = list("ABCDE")


def _seed_for(case_id: str) -> int:
    digest = hashlib.sha256(case_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _synth_address(rng: random.Random) -> str:
    number = rng.randint(1, 350)
    postcode = f"ZX{rng.randint(1, 9)} {rng.randint(1, 9)}{rng.choice('ABCDEFGH')}{rng.choice('ABCDEFGH')}"
    return f"{number} {rng.choice(STREETS)}, {rng.choice(TOWNS)}, {postcode}"


def _synth_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def _synth_date(rng: random.Random) -> str:
    year = rng.randint(2021, 2027)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


def _gen_value(field_key: str, rng: random.Random, address: str) -> str:
    key = field_key.lower()
    if key == "property_address":
        return address
    if key.endswith("_date") or key in {"valid_until"}:
        return _synth_date(rng)
    if key in {"engineer_name", "electrician_name", "assessor_name", "clerk_name",
               "landlord_name", "tenant_full_name", "tenant_name"}:
        return _synth_name(rng)
    if key == "company_name":
        return rng.choice(COMPANIES)
    if key in {"gas_safe_reg", "registration_number", "certificate_number"}:
        return str(rng.randint(100000, 999999))
    if key in {"current_rating", "epc_rating"}:
        return rng.choice(RATINGS)
    if key in {"deposit_amount", "monthly_rent_amount"}:
        return f"£{rng.choice(AMOUNTS):,}"
    if key == "scheme_name":
        return rng.choice(SCHEMES)
    if key in {"result", "overall_result"}:
        return rng.choice(RESULTS)
    if key == "appliances_tested":
        return "Boiler, Gas Hob, Gas Fire"
    if key == "observations":
        return "C3 recommendation noted, no immediate action required"
    if key == "door_location":
        return rng.choice(DOOR_LOCATIONS)
    if key == "property_condition_summary":
        return "Good condition throughout, no damage noted"
    return f"{field_key.replace('_', ' ').title()} {rng.randint(1, 999)}"


def _garble(value: str, rng: random.Random) -> str:
    """Perturb a value so exact match fails but token overlap is partial."""
    s = str(value)
    if not s:
        return s
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        digits = [i for i, c in enumerate(s) if c.isdigit()]
        i, j = rng.sample(digits, 2)
        chars = list(s)
        chars[i], chars[j] = chars[j], chars[i]
        return "".join(chars)
    tokens = s.split()
    if len(tokens) > 1:
        # Drop the last token (e.g. a postcode or surname) -> partial overlap.
        return " ".join(tokens[:-1])
    idx = rng.randrange(len(s))
    replacement = "x" if s[idx].lower() != "x" else "y"
    return s[:idx] + replacement + s[idx + 1:]


def _wrong_label(true_label: str, rng: random.Random) -> str:
    others = [t for t in config.DOC_TYPES if t != true_label]
    return rng.choice(others)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def _render_page(title: str, rows: list[tuple[str, str]]) -> Image.Image:
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    font_title = load_font(TITLE_SIZE, bold=True)
    font_label = load_font(LABEL_SIZE, bold=True)
    font_value = load_font(VALUE_SIZE, bold=False)
    text_area = W - 2 * MARGIN

    y = MARGIN
    for line in wrap_text(draw, title, font_title, text_area):
        draw.text((MARGIN, y), line, fill="black", font=font_title)
        y += TITLE_SIZE + 8
    y += 6
    draw.line([(MARGIN, y), (W - MARGIN, y)], fill="#111111", width=3)
    y += 20

    for label, value in rows:
        draw.text((MARGIN, y), f"{label}:", fill="#111111", font=font_label)
        y += LABEL_SIZE + 4
        for vline in wrap_text(draw, str(value), font_value, text_area - 24):
            draw.text((MARGIN + 24, y), vline, fill="#222222", font=font_value)
            y += VALUE_SIZE + 4
        y += 10
        if y > H - MARGIN - 50:
            break
    return img


def _apply_edge_transform(img: Image.Image, edge_case: str | None) -> Image.Image:
    if edge_case == "rotated":
        return img.rotate(90, expand=True, fillcolor="white")
    if edge_case == "poor_ocr":
        img = img.filter(ImageFilter.GaussianBlur(radius=1.4))
        img = ImageEnhance.Contrast(img).enhance(0.55)
        img = img.rotate(2, expand=False, fillcolor="white")
    return img


def _render_pdf(
    title: str,
    rows: list[tuple[str, str]],
    edge_case: str | None,
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if edge_case == "multi_page" and rows:
        # Split rows across up to 3 pages.
        chunk = max(1, (len(rows) + 2) // 3)
        pages = [rows[i:i + chunk] for i in range(0, len(rows), chunk)] or [rows]
        images = [_render_page(title if i == 0 else f"{title} (cont.)", page)
                  for i, page in enumerate(pages)]
        images[0].save(out_path, "PDF", save_all=True, append_images=images[1:])
        return
    img = _apply_edge_transform(_render_page(title, rows), edge_case)
    img.save(out_path, "PDF")


# --------------------------------------------------------------------------
# Case construction
# --------------------------------------------------------------------------


def _doc_type_field_config() -> dict[str, dict[str, Any]]:
    """Map canonical label -> {field_keys, field_labels, required_fields}."""
    config.setup_environment()
    from portal_new import document_config

    by_label: dict[str, dict[str, Any]] = {}
    for cfg in document_config.get_document_configs(str(config.EVAL_DB_PATH)):
        labels = {f["field_key"]: f["field_label"] for f in cfg["extraction_fields"]}
        by_label[cfg["label"]] = {
            "field_keys": cfg["field_keys"],
            "field_labels": labels,
            "required_fields": cfg["required_fields"],
        }
    return by_label


def _build_case(
    case_id: str,
    doc_type: str,
    edge_case: str | None,
    schema: dict[str, Any],
) -> dict[str, Any]:
    rng = random.Random(_seed_for(case_id))
    field_keys: list[str] = list(schema["field_keys"])
    field_labels: dict[str, str] = schema["field_labels"]
    required: list[str] = list(schema["required_fields"])

    address = _synth_address(rng)
    gt_fields = {key: _gen_value(key, rng, address) for key in field_keys}

    # missing_fields: genuinely drop up to two non-address required fields.
    if edge_case == "missing_fields":
        droppable = [k for k in required if k != "property_address"]
        rng.shuffle(droppable)
        for key in droppable[:2]:
            gt_fields[key] = ""

    # Recording starts from ground truth then gets seeded noise.
    extraction = dict(gt_fields)
    for key in field_keys:
        value = extraction.get(key, "")
        if not value:
            continue
        prob_drop, prob_garble = 0.03, 0.05
        if edge_case == "poor_ocr":
            prob_drop, prob_garble = 0.08, 0.22
        elif edge_case == "multi_page":
            prob_garble = 0.10
        roll = rng.random()
        if roll < prob_drop:
            extraction[key] = ""
        elif roll < prob_drop + prob_garble:
            extraction[key] = _garble(value, rng)

    detection = doc_type
    if edge_case == "detection_error":
        detection = _wrong_label(doc_type, rng)
    elif edge_case == "poor_ocr" and rng.random() < 0.2:
        detection = _wrong_label(doc_type, rng)

    # Render rows from non-empty ground-truth fields.
    rows = [(field_labels.get(k, k.replace("_", " ").title()), gt_fields[k])
            for k in field_keys if gt_fields.get(k)]
    title = doc_type.upper()
    pdf_rel = f"pdfs/{case_id}.pdf"
    _render_pdf(title, rows, edge_case, config.GOLDEN_DIR / pdf_rel)

    return {
        "id": case_id,
        "doc_type": doc_type,
        "edge_case": edge_case,
        "pdf_path": pdf_rel,
        "ground_truth": {"fields": gt_fields, "required_fields": required},
        "recording": {"detection": detection, "extraction": json.dumps(extraction, ensure_ascii=False)},
    }


def _build_other_case(case_id: str) -> dict[str, Any]:
    rng = random.Random(_seed_for(case_id))
    address = _synth_address(rng)
    rows = [
        ("Document", rng.choice(["Council Tax Bill", "Welcome Letter", "Utility Statement"])),
        ("Reference", str(rng.randint(10000, 99999))),
        ("Property Address", address),
        ("Date", _synth_date(rng)),
        ("Amount", f"£{rng.choice(AMOUNTS):,}"),
    ]
    pdf_rel = f"pdfs/{case_id}.pdf"
    _render_pdf("MISCELLANEOUS CORRESPONDENCE", rows, None, config.GOLDEN_DIR / pdf_rel)
    return {
        "id": case_id,
        "doc_type": config.OTHER_LABEL,
        "edge_case": "other_type",
        "pdf_path": pdf_rel,
        "ground_truth": {"fields": {}, "required_fields": []},
        "recording": {"detection": config.OTHER_LABEL, "extraction": "{}"},
    }


def build_dataset(out_path: Path | None = None) -> dict[str, Any]:
    """Generate all PDFs and return the manifest dict (also written to disk)."""
    out_path = out_path or config.MANIFEST_PATH
    schemas = _doc_type_field_config()

    cases: list[dict[str, Any]] = []
    for doc_type in config.DOC_TYPES:
        slug = TYPE_SLUGS[doc_type]
        schema = schemas.get(doc_type)
        if schema is None:
            raise RuntimeError(f"No document_config schema for '{doc_type}'")
        for n in range(1, CASES_PER_TYPE + 1):
            case_id = f"{slug}_{n:03d}"
            edge = EDGE_LAYOUT.get(n)
            cases.append(_build_case(case_id, doc_type, edge, schema))

    for n in range(1, OTHER_COUNT + 1):
        cases.append(_build_other_case(f"other_{n:03d}"))

    manifest = {
        "version": 1,
        "doc_types": config.DOC_TYPES,
        "count": len(cases),
        "cases": cases,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the MorphIQ golden eval dataset.")
    parser.add_argument("--out", type=str, default=str(config.MANIFEST_PATH),
                        help="Manifest output path (default: eval/golden/manifest.json)")
    args = parser.parse_args()

    manifest = build_dataset(Path(args.out))

    counts: dict[str, int] = {}
    edge_counts: dict[str, int] = {}
    for case in manifest["cases"]:
        counts[case["doc_type"]] = counts.get(case["doc_type"], 0) + 1
        edge_counts[case["edge_case"] or "happy"] = edge_counts.get(case["edge_case"] or "happy", 0) + 1

    pdf_count = len(list(config.PDFS_DIR.glob("*.pdf")))
    print(f"\n  Golden dataset: {manifest['count']} cases, {pdf_count} PDFs")
    print(f"  Manifest: {args.out}")
    print("  Per doc type:")
    for doc_type, n in sorted(counts.items()):
        print(f"    {doc_type:<32} {n}")
    print("  Edge cases:")
    for edge, n in sorted(edge_counts.items()):
        print(f"    {edge:<20} {n}")
    if pdf_count != manifest["count"]:
        print(f"  WARNING: expected {manifest['count']} PDFs, found {pdf_count}")
        sys.exit(1)
    print()


if __name__ == "__main__":
    main()
