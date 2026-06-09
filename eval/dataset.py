"""Golden dataset loading.

The dataset is a single committed ``manifest.json`` listing every case with its
ground truth and its recorded (synthetic) model responses. The PDFs themselves
are generated on demand (gitignored) by ``eval/golden/generate_golden.py``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eval import config


@dataclass
class GoldenCase:
    id: str
    doc_type: str  # ground-truth document type label
    pdf_path: Path  # absolute path to the (generated) PDF
    ground_truth: dict[str, Any]  # {"fields": {...}, "required_fields": [...]}
    recording: dict[str, str]  # {"detection": str, "extraction": str}
    edge_case: str | None = None

    @property
    def expected_fields(self) -> dict[str, Any]:
        return self.ground_truth.get("fields") or {}

    @property
    def required_fields(self) -> list[str]:
        return list(self.ground_truth.get("required_fields") or [])


def load_manifest(manifest_path: Path | None = None) -> list[dict[str, Any]]:
    path = manifest_path or config.MANIFEST_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"Golden manifest not found: {path}. "
            "Run `python eval/golden/generate_golden.py` to build the dataset."
        )
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    cases = data.get("cases") if isinstance(data, dict) else data
    if not isinstance(cases, list):
        raise ValueError(f"Malformed manifest (expected a list of cases): {path}")
    return cases


def load_cases(manifest_path: Path | None = None) -> list[GoldenCase]:
    cases: list[GoldenCase] = []
    for entry in load_manifest(manifest_path):
        rel = entry["pdf_path"]
        pdf_path = (config.GOLDEN_DIR / rel).resolve()
        cases.append(
            GoldenCase(
                id=entry["id"],
                doc_type=entry["doc_type"],
                pdf_path=pdf_path,
                ground_truth=entry.get("ground_truth") or {},
                recording=entry.get("recording") or {},
                edge_case=entry.get("edge_case"),
            )
        )
    return cases


def missing_pdfs(cases: list[GoldenCase]) -> list[GoldenCase]:
    return [case for case in cases if not case.pdf_path.is_file()]
