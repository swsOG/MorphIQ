"""Evaluation runners that drive the *real* pipeline with an injected client.

Shared helpers here build the throwaway DOC folder that ``ai_prefill.prefill_doc``
expects, and reuse ``compute_quality_assessment`` to score the ground truth with
the exact same logic the pipeline uses for predictions.
"""

from __future__ import annotations

import base64
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

_PDF_NAME = "document.pdf"


def read_pdf_b64(pdf_path: Path) -> str:
    with Path(pdf_path).open("rb") as handle:
        return base64.b64encode(handle.read()).decode("ascii")


def make_doc_folder(pdf_path: Path, doc_type: str) -> Path:
    """Create a temp DOC folder with the PDF + a review.json for prefill_doc."""
    folder = Path(tempfile.mkdtemp(prefix="eval_doc_"))
    shutil.copyfile(pdf_path, folder / _PDF_NAME)
    review = {
        "doc_id": pdf_path.stem,
        "doc_type": doc_type,
        "fields": {},
        "files": {"pdf": _PDF_NAME},
    }
    with (folder / "review.json").open("w", encoding="utf-8") as handle:
        json.dump(review, handle)
    return folder


def read_review(folder: Path) -> dict[str, Any]:
    with (folder / "review.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ground_truth_quality(doc_type: str, fields: dict[str, Any]) -> tuple[int, bool]:
    """Score ground-truth fields with the pipeline's own quality logic."""
    import ai_prefill

    review = {"doc_type": doc_type, "fields": dict(fields)}
    ai_prefill.compute_quality_assessment(review)
    return int(review.get("completeness_score", 0)), bool(review.get("needs_attention", True))


def field_keys_for(doc_type: str) -> list[str]:
    import ai_prefill

    config = ai_prefill.get_document_config(doc_type)
    if not config:
        return []
    return list(config.get("field_keys") or [])
