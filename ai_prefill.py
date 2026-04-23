import argparse
import base64
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
from portal_new.ai_runtime import generate_gemini_text, get_prefill_model_name, load_project_env
from portal_new import document_config


load_project_env(Path(__file__).parent)


BASE = Path(__file__).resolve().parent
CLIENTS_DIR = BASE / "Clients"
DATABASE_URL = os.environ.get("DATABASE_URL", str(BASE / "portal.db"))


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


def get_document_config(doc_type: str) -> Dict[str, Any] | None:
    return document_config.find_document_config(doc_type, DATABASE_URL)


def get_recognized_doc_types() -> list[str]:
    labels = document_config.get_detection_document_labels(DATABASE_URL)
    return labels or ["Tenancy Agreement", "Gas Safety Certificate", "EICR", "EPC", "Deposit Protection Certificate", "Inventory"]


def build_extraction_prompt(review_data: Dict[str, Any], config: Dict[str, Any]) -> str:
    fields = config.get("extraction_fields") or []
    field_keys = [field["field_key"] for field in fields]
    existing = review_data.get("fields") or {}
    existing_snippet = {field_key: existing.get(field_key, "") for field_key in field_keys}
    field_lines = []
    for field in fields:
        requirement = "required" if field.get("is_required") else "optional"
        field_lines.append(f"  - {field['field_key']} ({field['field_label']}; {requirement})")

    return (
        f"You are an assistant that reads a {config['label']} and extracts key fields.\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        f"{chr(10).join(field_lines)}\n\n"
        "Use the PDF content I provide, not your own knowledge. "
        "Dates should be ISO format like 2026-01-31 when clearly stated. "
        "If you are unsure about a field, use an empty string.\n\n"
        "Existing values from the system (you may correct these if they are wrong):\n"
        f"{json.dumps(existing_snippet, ensure_ascii=False, indent=2)}\n\n"
        "Again, respond with JSON only, no commentary."
    )


def get_model_name(task_type: str) -> str:
    return get_prefill_model_name(task_type)


def get_ai_provider() -> str:
    return "gemini"


def call_gemini_with_pdf(pdf_b64: str, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    return generate_gemini_text(
        model=model or get_model_name("extraction"),
        prompt=f"{system_prompt}\n\n{user_prompt}".strip(),
        inline_pdf_b64=pdf_b64,
    )


def call_claude_with_pdf(pdf_b64: str, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    raise RuntimeError("Claude provider is no longer supported")


def call_model_with_pdf(pdf_b64: str, system_prompt: str, user_prompt: str) -> str:
    provider = get_ai_provider()
    if provider == "gemini":
        return call_gemini_with_pdf(
            pdf_b64,
            system_prompt,
            user_prompt,
            model=get_model_name("extraction"),
        )
    return call_claude_with_pdf(pdf_b64, system_prompt, user_prompt)


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


DETECTION_SYSTEM = "You classify scanned property documents."

EXTRACTION_SYSTEM = "You are a careful assistant that extracts structured data from scanned property documents."


def compute_quality_assessment(review: Dict[str, Any]) -> None:
    """Compute completeness_score, missing_fields, and needs_attention in-place."""
    doc_type = (review.get("doc_type") or "").strip()
    config = get_document_config(doc_type)
    if not config:
        review["completeness_score"] = 0
        review["missing_fields"] = ["doc_type"]
        review["needs_attention"] = True
        return

    required = config.get("required_fields") or []
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
    return any(t.lower() in normalized.lower() for t in get_recognized_doc_types())


def _normalize_doc_type(raw: str) -> str:
    """Map API response to exact label from RECOGNIZED_DOC_TYPES."""
    if not raw or not raw.strip():
        return ""
    raw = raw.strip()
    for label in get_recognized_doc_types():
        if label.lower() in raw.lower():
            return label
    return raw


def detect_doc_type_from_pdf(pdf_b64: str) -> str:
    """Call Gemini to classify the document; returns one of RECOGNIZED_DOC_TYPES (or raw response)."""
    labels = get_recognized_doc_types()
    detection_user = (
        "Look at this document and identify what type it is. "
        "Reply with ONLY one of these exact labels, nothing else: "
        + ", ".join(labels)
    )
    raw = call_ai_with_pdf(pdf_b64, DETECTION_SYSTEM, detection_user, "detection")
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

    config = get_document_config(doc_type)
    if not config:
        log(f"Skipping AI prefill for doc_type '{doc_type}' (no template configured)", doc_folder)
        compute_quality_assessment(review)
        save_review(doc_folder, review)
        log(f"Quality assessment: score={review['completeness_score']}%, "
            f"missing={review['missing_fields']}, needs_attention={review['needs_attention']}", doc_folder)
        return

    normalized = config["label"]
    log(f"Starting AI prefill for {normalized}", doc_folder)

    if pdf_b64 is None:
        pdf_b64 = read_pdf_base64(doc_folder, review)
    system_prompt = EXTRACTION_SYSTEM
    user_prompt = build_extraction_prompt(review, config)

    model_raw = call_ai_with_pdf(pdf_b64, system_prompt, user_prompt, "extraction")
    ai_fields = parse_json_from_ai(model_raw)

    fields = review.get("fields") or {}
    for key in config.get("field_keys") or []:
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

