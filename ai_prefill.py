import argparse
import base64
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
import urllib.request
import urllib.error


env_path = Path(__file__).parent / ".env"
if env_path.exists():
    try:
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.lstrip().startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ[key] = val
    except Exception:
        pass


BASE = Path(r"C:\ScanSystem_v2")
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


def call_claude_with_pdf(
    pdf_b64: str,
    system_prompt: str,
    user_prompt: str,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    url = "https://api.anthropic.com/v1/messages"

    content = [
        {
            "type": "text",
            "text": user_prompt,
        },
        {
            # NOTE: Anthropic supports multimodal inputs. This structure assumes
            # a document-style input encoded as base64. Adjust if your account
            # uses a different format for PDFs.
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_b64,
            },
        },
    ]

    body = {
        "model": model,
        "max_tokens": 1024,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
    }

    data = json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_data = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic API error {e.code}: {error_body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Error calling Anthropic API: {e}") from e

    payload = json.loads(resp_data)
    content_items = payload.get("content") or []
    if not content_items:
        raise RuntimeError("No content returned from Claude")
    # Assume first content item is text
    first = content_items[0]
    if first.get("type") == "text":
        return first.get("text", "")
    # Fallback: try to find any text item
    for item in content_items:
        if item.get("type") == "text":
            return item.get("text", "")
    raise RuntimeError("No text content returned from Claude")


def parse_json_from_claude(text: str) -> Dict[str, Any]:
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


def prefill_doc(doc_folder: Path) -> None:
    review = load_review(doc_folder)
    doc_type = (
        review.get("doc_type_template")
        or review.get("doc_type")
        or ""
    ).strip()
    doc_type_lower = doc_type.lower()

    # Treat any doc_type containing the word "tenancy" as a tenancy agreement.
    if "tenancy" not in doc_type_lower:
        log(f"Skipping AI prefill for doc_type '{doc_type}' (no template configured)", doc_folder)
        return

    log("Starting AI prefill for tenancy agreement", doc_folder)

    pdf_b64 = read_pdf_base64(doc_folder, review)

    system_prompt = "You are a careful assistant that extracts structured data from property tenancy agreements."
    user_prompt = build_tenancy_agreement_prompt(review)

    claude_raw = call_claude_with_pdf(pdf_b64, system_prompt, user_prompt)
    ai_fields = parse_json_from_claude(claude_raw)

    target_keys = [
        "property_address",
        "tenant_full_name",
        "landlord_name",
        "start_date",
        "end_date",
        "monthly_rent_amount",
        "deposit_amount",
        "agreement_date",
    ]

    fields = review.get("fields") or {}
    for key in target_keys:
        if key in ai_fields and ai_fields[key] is not None:
            fields[key] = str(ai_fields[key])
    review["fields"] = fields
    review["status"] = "ai_prefilled"

    save_review(doc_folder, review)
    log("AI prefill completed successfully (status=ai_prefilled)", doc_folder)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI prefill for DOC-XXXXX folder using Claude Sonnet.")
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

