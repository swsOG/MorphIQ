import json
import os
from pathlib import Path
import urllib.error
import urllib.request


GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"


def load_project_env(project_root: str | Path) -> None:
    env_path = Path(project_root) / ".env"
    if not env_path.exists():
        return

    try:
        with env_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    except OSError:
        return


def get_required_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def get_chat_model_name() -> str:
    return (os.getenv("GEMINI_MODEL_CHAT") or GEMINI_DEFAULT_MODEL).strip()


def get_prefill_model_name(task_type: str) -> str:
    task_key = (task_type or "").strip().lower()
    if task_key not in {"detection", "extraction"}:
        raise RuntimeError(f"Unsupported task type: {task_type}")
    env_name = "GEMINI_MODEL_DETECTION" if task_key == "detection" else "GEMINI_MODEL_EXTRACTION"
    return (os.getenv(env_name) or GEMINI_DEFAULT_MODEL).strip()


def generate_gemini_text(
    *,
    api_key: str | None = None,
    model: str,
    prompt: str,
    inline_pdf_b64: str | None = None,
    timeout_seconds: int = 60,
) -> str:
    key = api_key or get_required_env("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    parts: list[dict] = [{"text": prompt}]
    if inline_pdf_b64:
        parts.append(
            {
                "inline_data": {
                    "mime_type": "application/pdf",
                    "data": inline_pdf_b64,
                }
            }
        )

    body = {"contents": [{"parts": parts}]}
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API error {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Error calling Gemini API: {exc}") from exc

    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError("No candidates returned from Gemini")

    content = candidates[0].get("content") or {}
    text_parts = [part.get("text", "") for part in (content.get("parts") or []) if part.get("text")]
    text = "\n".join(text_parts).strip()
    if not text:
        raise RuntimeError("No text content returned from Gemini")
    return text
