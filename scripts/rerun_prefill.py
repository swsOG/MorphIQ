"""
Re-run ai_prefill.py for DOC folders that are still New or have unknown doc type.

Usage:
  python rerun_prefill.py "Oakwood Lettings" "Riverside Property Management"
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# Deploy root: same directory as this script (no hardcoded drive/path).
BASE = Path(__file__).resolve().parent.parent
CLIENTS_DIR = BASE / "Clients"
AI_PREFILL_SCRIPT = BASE / "ai_prefill.py"

DOC_FOLDER_PATTERN = re.compile(r"^DOC-\d{5}$")


def should_rerun_prefill(review: dict) -> bool:
    status = review.get("status")
    if status == "New":
        return True
    doc_type = review.get("doc_type")
    if doc_type is None:
        return True
    if isinstance(doc_type, str) and doc_type.strip() == "":
        return True
    if doc_type == "Unknown":
        return True
    return False


def find_doc_folders(batches_root: Path) -> list[Path]:
    """All DOC-xxxxx directories under Batches/, deepest paths first for stable ordering."""
    found: list[Path] = []
    if not batches_root.is_dir():
        return found
    for p in batches_root.rglob("*"):
        if p.is_dir() and DOC_FOLDER_PATTERN.fullmatch(p.name):
            found.append(p)
    return sorted(found)


def run_ai_prefill_subprocess(client_name: str, doc_folder: Path) -> subprocess.CompletedProcess[str]:
    """Match auto_ocr_watch.run_ai_prefill: sys.executable + script path + doc folder."""
    proc: subprocess.CompletedProcess[str] | None = None
    for attempt in range(3):
        proc = subprocess.run(
            [sys.executable, str(AI_PREFILL_SCRIPT), str(doc_folder)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
        )
        time.sleep(5)
        if proc.returncode == 0:
            break
        out = proc.stdout or ""
        if proc.returncode != 0 and "429" in out and attempt < 2:
            print(
                f"[{client_name}] {doc_folder.name} rate limited, waiting 60s (attempt {attempt + 2}/3)...",
                flush=True,
            )
            time.sleep(60)
            continue
        break
    assert proc is not None
    return proc


def process_client(client_name: str) -> None:
    batches_root = CLIENTS_DIR / client_name / "Batches"
    if not batches_root.is_dir():
        print(f"[{client_name}] SKIP: Batches folder not found: {batches_root}", flush=True)
        return

    if not AI_PREFILL_SCRIPT.is_file():
        print(
            f"[{client_name}] ERROR: ai_prefill.py not found at {AI_PREFILL_SCRIPT}",
            flush=True,
        )
        return

    doc_folders = find_doc_folders(batches_root)
    for doc_folder in doc_folders:
        review_path = doc_folder / "review.json"
        if not review_path.is_file():
            print(
                f"[{client_name}] {doc_folder.name} ERROR: missing review.json",
                flush=True,
            )
            continue
        try:
            with review_path.open("r", encoding="utf-8") as f:
                review = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(
                f"[{client_name}] {doc_folder.name} ERROR: cannot read review.json ({e})",
                flush=True,
            )
            continue

        if not should_rerun_prefill(review):
            print(
                f"[{client_name}] {doc_folder} skipped (status/doc_type OK)",
                flush=True,
            )
            continue

        try:
            proc = run_ai_prefill_subprocess(client_name, doc_folder)
        except subprocess.TimeoutExpired:
            print(
                f"[{client_name}] {doc_folder} ERROR: ai_prefill timed out after 180s",
                flush=True,
            )
            continue
        except Exception as e:
            print(
                f"[{client_name}] {doc_folder} ERROR: {e}",
                flush=True,
            )
            continue

        out = (proc.stdout or "").strip()
        if proc.returncode != 0:
            detail = f" {out}" if out else ""
            print(
                f"[{client_name}] {doc_folder} error (exit {proc.returncode}){detail}",
                flush=True,
            )
        else:
            print(f"[{client_name}] {doc_folder} prefilled", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-run ai_prefill for DOC folders with status New or unknown doc_type."
    )
    parser.add_argument(
        "clients",
        nargs="+",
        help='One or more client folder names under Clients/, e.g. "Oakwood Lettings"',
    )
    args = parser.parse_args()

    for client_name in args.clients:
        process_client(client_name)


if __name__ == "__main__":
    main()
