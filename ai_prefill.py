import argparse
import base64
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
from portal_new.ai_runtime import generate_gemini_text, get_prefill_model_name, load_project_env


load_project_env(Path(__file__).parent)


BASE = Path(__file__).resolve().parent
CLIENTS_DIR = BASE / "Clients"


def log(message: str, doc_folder: Path) -> None:
    """Append a log line to the client's pipeline.log and echo to stdout."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [AI_PREFILL] {message}\n"

    # Try to infer client name from the DOC folder path: .../Clients/<client>/Batches/...
    client_name = None
    parts = list(doc_folder.resolve().parts)
    try:
        idx = parts.index("Clients")
        if idx + 1 < len(parts):
            client_name = parts[idx + 1]
    except ValueError:
        client_name = None

    if client_name:
        log_dir = CLIENTS_DIR / client_name / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "pipeline.log"
        try:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            # Fail silently for logging errors
            pass

    print(line, end="", flush=True)


def load_review(doc_folder: Path) -> Dict[str, Any]:
    review_path = doc_folder / "review.json"
    if not review_path.is_file():
        raise FileNotFoundError(f"review.json not found in {doc_folder}")
    with review_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_review(doc_folder: Path, review_data: Dict[str, Any]) -> None:
    review_path = doc_folder / "review.json"
    with review_path.open("w", encoding="utf-8") as f:
        json.dump(review_data, f, indent=2, ensure_ascii=False)


def read_pdf_base64(doc_folder: Path, review_data: Dict[str, Any]) -> str:
    files = review_data.get("files") or {}
    pdf_name = files.get("pdf")
    if not pdf_name:
        raise FileNotFoundError("No 'pdf' entry found in review.json['files']")
    pdf_path = doc_folder / pdf_name
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    with pdf_path.open("rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("ascii")


def build_tenancy_agreement_prompt(review_data: Dict[str, Any]) -> str:
    fields = [
        "property_address",
        "tenant_full_name",
        "landlord_name",
        "start_date",
        "end_date",
        "monthly_rent_amount",
        "deposit_amount",
        "agreement_date",
    ]
    existing = review_data.get("fields") or {}
    existing_snippet = {k: existing.get(k, "") for k in fields}

    return (
        "You are an assistant that reads a residential tenancy agreement and extracts key fields.\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "  - property_address (string)\n"
        "  - tenant_full_name (string)\n"
        "  - landlord_name (string)\n"
        "  - start_date (ISO date like 2026-01-31)\n"
        "  - end_date (ISO date like 2027-01-30)\n"
        "  - monthly_rent_amount (numeric or string, just the amount and currency if present)\n"
        "  - deposit_amount (numeric or string)\n"
        "  - agreement_date (ISO date if clearly stated, otherwise empty string)\n\n"
        "Use the PDF content I provide, not your own knowledge. "
        "If you are unsure about a field, use an empty string.\n\n"
        "Existing values from the system (you may correct these if they are wrong):\n"
        f"{json.dumps(existing_snippet, ensure_ascii=False, indent=2)}\n\n"
        "Again, respond with JSON only, no commentary."
    )


def build_gas_safety_prompt(review_data: Dict[str, Any]) -> str:
    fields = [
        "property_address",
        "engineer_name",
        "gas_safe_reg",
        "inspection_date",
        "expiry_date",
        "appliances_tested",
        "result",
    ]
    existing = review_data.get("fields") or {}
    existing_snippet = {k: existing.get(k, "") for k in fields}
    return (
        "You are an assistant that reads a Gas Safety Certificate and extracts key fields.\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "  - property_address (string)\n"
        "  - engineer_name (string)\n"
        "  - gas_safe_reg (string, registration number)\n"
        "  - inspection_date (ISO date like 2026-01-31)\n"
        "  - expiry_date (ISO date)\n"
        "  - appliances_tested (string, list or description of appliances)\n"
        "  - result (string: Pass or Fail)\n\n"
        "Use the PDF content I provide, not your own knowledge. "
        "If you are unsure about a field, use an empty string.\n\n"
        "Existing values from the system (you may correct these if they are wrong):\n"
        f"{json.dumps(existing_snippet, ensure_ascii=False, indent=2)}\n\n"
        "Again, respond with JSON only, no commentary."
    )


def build_eicr_prompt(review_data: Dict[str, Any]) -> str:
    fields = [
        "property_address",
        "electrician_name",
        "company_name",
        "registration_number",
        "inspection_date",
        "next_inspection_date",
        "overall_result",
        "observations",
    ]
    existing = review_data.get("fields") or {}
    existing_snippet = {k: existing.get(k, "") for k in fields}
    return (
        "You are an assistant that reads an EICR (Electrical Installation Condition Report) and extracts key fields.\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "  - property_address (string)\n"
        "  - electrician_name (string)\n"
        "  - company_name (string)\n"
        "  - registration_number (string)\n"
        "  - inspection_date (ISO date like 2026-01-31)\n"
        "  - next_inspection_date (ISO date)\n"
        "  - overall_result (string: Satisfactory or Unsatisfactory)\n"
        "  - observations (string, summary of findings)\n\n"
        "Use the PDF content I provide, not your own knowledge. "
        "If you are unsure about a field, use an empty string.\n\n"
        "Existing values from the system (you may correct these if they are wrong):\n"
        f"{json.dumps(existing_snippet, ensure_ascii=False, indent=2)}\n\n"
        "Again, respond with JSON only, no commentary."
    )


def build_epc_prompt(review_data: Dict[str, Any]) -> str:
    fields = [
        "property_address",
        "epc_rating",
        "assessor_name",
        "assessment_date",
        "expiry_date",
    ]
    existing = review_data.get("fields") or {}
    existing_snippet = {k: existing.get(k, "") for k in fields}
    return (
        "You are an assistant that reads an EPC (Energy Performance Certificate) and extracts key fields.\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "  - property_address (string)\n"
        "  - epc_rating (string, e.g. A, B, C, D, E, F, G)\n"
        "  - assessor_name (string)\n"
        "  - assessment_date (ISO date like 2026-01-31)\n"
        "  - expiry_date (ISO date)\n\n"
        "Use the PDF content I provide, not your own knowledge. "
        "If you are unsure about a field, use an empty string.\n\n"
        "Existing values from the system (you may correct these if they are wrong):\n"
        f"{json.dumps(existing_snippet, ensure_ascii=False, indent=2)}\n\n"
        "Again, respond with JSON only, no commentary."
    )


def build_deposit_protection_prompt(review_data: Dict[str, Any]) -> str:
    fields = [
        "property_address",
        "tenant_full_name",
        "deposit_amount",
        "scheme_name",
        "certificate_number",
        "protection_date",
    ]
    existing = review_data.get("fields") or {}
    existing_snippet = {k: existing.get(k, "") for k in fields}
    return (
        "You are an assistant that reads a Deposit Protection Certificate and extracts key fields.\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "  - property_address (string)\n"
        "  - tenant_full_name (string)\n"
        "  - deposit_amount (numeric or string)\n"
        "  - scheme_name (string, name of the protection scheme)\n"
        "  - certificate_number (string)\n"
        "  - protection_date (ISO date if present)\n\n"
        "Use the PDF content I provide, not your own knowledge. "
        "If you are unsure about a field, use an empty string.\n\n"
        "Existing values from the system (you may correct these if they are wrong):\n"
        f"{json.dumps(existing_snippet, ensure_ascii=False, indent=2)}\n\n"
        "Again, respond with JSON only, no commentary."
    )


def build_inventory_prompt(review_data: Dict[str, Any]) -> str:
    fields = [
        "property_address",
        "clerk_name",
        "inspection_date",
        "property_condition_summary",
    ]
    existing = review_data.get("fields") or {}
    existing_snippet = {k: existing.get(k, "") for k in fields}
    return (
        "You are an assistant that reads a property Inventory and extracts key fields.\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "  - property_address (string)\n"
        "  - clerk_name (string, person who did the inventory)\n"
        "  - inspection_date (ISO date like 2026-01-31)\n"
        "  - property_condition_summary (string, overall condition or key notes)\n\n"
        "Use the PDF content I provide, not your own knowledge. "
        "If you are unsure about a field, use an empty string.\n\n"
        "Existing values from the system (you may correct these if they are wrong):\n"
        f"{json.dumps(existing_snippet, ensure_ascii=False, indent=2)}\n\n"
        "Again, respond with JSON only, no commentary."
    )


def get_model_name(task_type: str) -> str:
    return get_prefill_model_name(task_type)


def call_ai_with_pdf(pdf_b64: str, system_prompt: str, user_prompt: str, task_type: str) -> str:
    model = get_model_name(task_type)
    prompt = f"{system_prompt}\n\n{user_prompt}".strip()
    return generate_gemini_text(model=model, prompt=prompt, inline_pdf_b64=pdf_b64)


def parse_json_from_ai(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    # Handle ```json ... ``` wrappers if present
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1] if not parts[0].strip() else parts[2]
        cleaned = cleaned.strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


# Recognized document types for extraction. Used for auto-detect and prompt selection.
RECOGNIZED_DOC_TYPES = [
    "Tenancy Agreement",
    "Gas Safety Certificate",
    "EICR",
    "EPC",
    "Deposit Protection Certificate",
    "Inventory",
]

DETECTION_SYSTEM = "You classify scanned property documents."
DETECTION_USER = (
    "Look at this document and identify what type it is. "
    "Reply with ONLY one of these exact labels, nothing else: "
    "Tenancy Agreement, Gas Safety Certificate, EICR, EPC, Deposit Protection Certificate, Inventory"
)

EXTRACTION_SYSTEM = "You are a careful assistant that extracts structured data from scanned property documents."

# Map normalized doc_type to (prompt_builder_fn, list of field keys).
DOC_TYPE_CONFIG: Dict[str, Any] = {
    "Tenancy Agreement": (build_tenancy_agreement_prompt, [
        "property_address", "tenant_full_name", "landlord_name", "start_date",
        "end_date", "monthly_rent_amount", "deposit_amount", "agreement_date",
    ]),
    "Gas Safety Certificate": (build_gas_safety_prompt, [
        "property_address", "engineer_name", "gas_safe_reg", "inspection_date",
        "expiry_date", "appliances_tested", "result",
    ]),
    "EICR": (build_eicr_prompt, [
        "property_address", "electrician_name", "company_name", "registration_number",
        "inspection_date", "next_inspection_date", "overall_result", "observations",
    ]),
    "EPC": (build_epc_prompt, [
        "property_address", "epc_rating", "assessor_name", "assessment_date", "expiry_date",
    ]),
    "Deposit Protection Certificate": (build_deposit_protection_prompt, [
        "property_address", "tenant_full_name", "deposit_amount", "scheme_name",
        "certificate_number", "protection_date",
    ]),
    "Inventory": (build_inventory_prompt, [
        "property_address", "clerk_name", "inspection_date", "property_condition_summary",
    ]),
}


REQUIRED_FIELDS: Dict[str, list] = {
    "Gas Safety Certificate": [
        "property_address", "engineer_name", "gas_safe_reg",
        "inspection_date", "expiry_date", "result",
    ],
    "EICR": [
        "property_address", "electrician_name", "inspection_date",
        "next_inspection_date", "result",
    ],
    "EPC": [
        "property_address", "current_rating", "assessment_date", "expiry_date",
    ],
    "Tenancy Agreement": [
        "property_address", "tenant_full_name", "start_date", "monthly_rent_amount",
    ],
    "Deposit Protection Certificate": [
        "property_address", "tenant_name", "deposit_amount", "protection_date",
    ],
    "Inventory": [
        "property_address", "inspection_date",
    ],
}


def compute_quality_assessment(review: Dict[str, Any]) -> None:
    """Compute completeness_score, missing_fields, and needs_attention in-place."""
    doc_type = (review.get("doc_type") or "").strip()

    if doc_type not in REQUIRED_FIELDS:
        review["completeness_score"] = 0
        review["missing_fields"] = ["doc_type"]
        review["needs_attention"] = True
        return

    required = REQUIRED_FIELDS[doc_type]
    fields = review.get("fields") or {}

    missing = []
    filled = 0
    for key in required:
        val = fields.get(key, "")
        if isinstance(val, str):
            val = val.strip()
        if val:
            filled += 1
        else:
            missing.append(key)

    total = len(required)
    score = int((filled / total) * 100) if total > 0 else 0

    property_address = (fields.get("property_address") or "").strip()
    review["completeness_score"] = score
    review["missing_fields"] = missing
    review["needs_attention"] = (not property_address) or (score < 70)


def _needs_doc_type_detection(doc_type: str) -> bool:
    """Return True if doc_type is empty, unknown, or generic and we should run detection."""
    if not doc_type or not doc_type.strip():
        return True
    lower = doc_type.strip().lower()
    if lower in ("unknown", "document", "generic"):
        return True
    return False


def _is_recognized_doc_type(doc_type: str) -> bool:
    """Return True if doc_type matches one of RECOGNIZED_DOC_TYPES (case-insensitive)."""
    if not doc_type or not doc_type.strip():
        return False
    normalized = doc_type.strip()
    return any(t.lower() in normalized.lower() for t in RECOGNIZED_DOC_TYPES)


def _normalize_doc_type(raw: str) -> str:
    """Map API response to exact label from RECOGNIZED_DOC_TYPES."""
    if not raw or not raw.strip():
        return ""
    raw = raw.strip()
    for label in RECOGNIZED_DOC_TYPES:
        if label.lower() in raw.lower():
            return label
    return raw


def detect_doc_type_from_pdf(pdf_b64: str) -> str:
    """Call Gemini to classify the document; returns one of RECOGNIZED_DOC_TYPES (or raw response)."""
    raw = call_ai_with_pdf(pdf_b64, DETECTION_SYSTEM, DETECTION_USER, "detection")
    return _normalize_doc_type(raw.strip())


def prefill_doc(doc_folder: Path) -> None:
    review = load_review(doc_folder)
    doc_type = (
        review.get("doc_type_template")
        or review.get("doc_type")
        or ""
    ).strip()
    pdf_b64 = None

    # Auto-detect document type if empty, unknown, or generic.
    if _needs_doc_type_detection(doc_type):
        log("Doc type empty or generic; running auto-detection", doc_folder)
        pdf_b64 = read_pdf_base64(doc_folder, review)
        detected = detect_doc_type_from_pdf(pdf_b64)
        if not detected:
            log("Auto-detection returned no type; marking as Unknown", doc_folder)
            review["doc_type"] = "Unknown"
            compute_quality_assessment(review)
            save_review(doc_folder, review)
            log(f"Quality assessment: score={review['completeness_score']}%, "
                f"missing={review['missing_fields']}, needs_attention={review['needs_attention']}", doc_folder)
            return
        doc_type = detected
        review["doc_type"] = doc_type

    # Resolve to exact label from RECOGNIZED_DOC_TYPES for config lookup.
    normalized = None
    for label in RECOGNIZED_DOC_TYPES:
        if label.lower() in doc_type.lower():
            normalized = label
            break
    if not normalized or normalized not in DOC_TYPE_CONFIG:
        log(f"Skipping AI prefill for doc_type '{doc_type}' (no template configured)", doc_folder)
        compute_quality_assessment(review)
        save_review(doc_folder, review)
        log(f"Quality assessment: score={review['completeness_score']}%, "
            f"missing={review['missing_fields']}, needs_attention={review['needs_attention']}", doc_folder)
        return

    log(f"Starting AI prefill for {normalized}", doc_folder)

    if pdf_b64 is None:
        pdf_b64 = read_pdf_base64(doc_folder, review)
    builder_fn, target_keys = DOC_TYPE_CONFIG[normalized]
    system_prompt = EXTRACTION_SYSTEM
    user_prompt = builder_fn(review)

    model_raw = call_ai_with_pdf(pdf_b64, system_prompt, user_prompt, "extraction")
    ai_fields = parse_json_from_ai(model_raw)

    fields = review.get("fields") or {}
    for key in target_keys:
        if key in ai_fields and ai_fields[key] is not None:
            fields[key] = str(ai_fields[key])
    review["fields"] = fields
    review["doc_type"] = normalized
    review["status"] = "ai_prefilled"

    compute_quality_assessment(review)
    save_review(doc_folder, review)
    log(f"AI prefill completed (status=ai_prefilled) — quality: score={review['completeness_score']}%, "
        f"missing={review['missing_fields']}, needs_attention={review['needs_attention']}", doc_folder)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI prefill for DOC-XXXXX folder using the configured Gemini models.")
    parser.add_argument("doc_folder", type=str, help="Path to DOC-XXXXX folder")
    args = parser.parse_args()

    folder = Path(args.doc_folder)
    if not folder.is_dir():
        raise SystemExit(f"Not a directory: {folder}")

    try:
        prefill_doc(folder)
    except Exception as e:
        log(f"AI prefill failed: {e}", folder)
        raise


if __name__ == "__main__":
    main()

