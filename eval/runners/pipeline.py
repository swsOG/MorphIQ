"""Pipeline runner: end-to-end detect -> extract (doc type left empty)."""

from __future__ import annotations

import shutil
from typing import Any

import ai_prefill

from eval.dataset import GoldenCase
from eval.metrics import field_exact_match, is_empty
from eval.runners import (
    field_keys_for,
    ground_truth_quality,
    make_doc_folder,
    read_review,
)


def _required_fields_all_correct(expected: dict, actual: dict, required: list[str]) -> bool:
    for key in required:
        exp = expected.get(key, "")
        if is_empty(exp):
            continue
        if not field_exact_match(exp, actual.get(key, "")):
            return False
    return True


def run_case(case: GoldenCase, client: Any) -> dict[str, Any]:
    # Empty doc_type forces prefill_doc to auto-detect, then extract.
    folder = make_doc_folder(case.pdf_path, doc_type="")
    try:
        ai_prefill.prefill_doc(folder, client=client)
        review = read_review(folder)
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    predicted_type = (review.get("doc_type") or "").strip()
    actual_fields = review.get("fields") or {}
    actual_score = int(review.get("completeness_score", 0))
    actual_attention = bool(review.get("needs_attention", True))

    gt_score, gt_attention = ground_truth_quality(case.doc_type, case.expected_fields)

    type_correct = predicted_type == case.doc_type
    fields_correct = _required_fields_all_correct(
        case.expected_fields, actual_fields, case.required_fields
    )

    return {
        "id": case.id,
        "edge_case": case.edge_case,
        "expected_type": case.doc_type,
        "predicted_type": predicted_type,
        "type_correct": type_correct,
        # end-to-end pass: right type AND all present required fields right
        "pipeline_correct": type_correct and fields_correct,
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
