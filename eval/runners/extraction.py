"""Extraction runner: run prefill_doc with the doc type known, score fields."""

from __future__ import annotations

import shutil
from typing import Any

import ai_prefill

from eval.dataset import GoldenCase
from eval.runners import (
    field_keys_for,
    ground_truth_quality,
    make_doc_folder,
    read_review,
)


def run_case(case: GoldenCase, client: Any) -> dict[str, Any]:
    folder = make_doc_folder(case.pdf_path, doc_type=case.doc_type)
    try:
        ai_prefill.prefill_doc(folder, client=client)
        review = read_review(folder)
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    actual_fields = review.get("fields") or {}
    actual_score = int(review.get("completeness_score", 0))
    actual_attention = bool(review.get("needs_attention", True))

    gt_score, gt_attention = ground_truth_quality(case.doc_type, case.expected_fields)

    return {
        "id": case.id,
        "edge_case": case.edge_case,
        "doc_type": case.doc_type,
        "field_keys": field_keys_for(case.doc_type),
        "required_fields": case.required_fields,
        "expected": case.expected_fields,
        "actual": actual_fields,
        "expected_completeness": gt_score,
        "actual_completeness": actual_score,
        "expected_attention": gt_attention,
        "actual_attention": actual_attention,
        "usage": list(getattr(client, "usages", [])),
    }
