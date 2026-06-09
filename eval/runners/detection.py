"""Detection runner: classify each golden PDF and compare to ground truth."""

from __future__ import annotations

from typing import Any

import ai_prefill

from eval.dataset import GoldenCase
from eval.runners import read_pdf_b64


def run_case(case: GoldenCase, client: Any) -> dict[str, Any]:
    pdf_b64 = read_pdf_b64(case.pdf_path)
    predicted = ai_prefill.detect_doc_type_from_pdf(pdf_b64, client=client)
    return {
        "id": case.id,
        "edge_case": case.edge_case,
        "expected": case.doc_type,
        "predicted": predicted,
        "correct": predicted == case.doc_type,
        "usage": list(getattr(client, "usages", [])),
    }
