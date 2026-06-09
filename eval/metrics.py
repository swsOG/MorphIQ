"""Pure metric computations for the eval harness.

No I/O, no global state, stdlib only — every function here is deterministic and
unit-testable. Pearson's r is computed manually to avoid a scipy/numpy
dependency.
"""

from __future__ import annotations

import math
import re
from typing import Any, Iterable, Sequence

# --------------------------------------------------------------------------
# String normalisation helpers
# --------------------------------------------------------------------------

_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"\w+")


def normalize_value(value: Any) -> str:
    """Case/whitespace-insensitive normal form for exact-match comparison."""
    text = "" if value is None else str(value)
    text = text.strip().casefold()
    text = _WS_RE.sub(" ", text)
    return text


def tokenize(value: Any) -> list[str]:
    text = "" if value is None else str(value)
    return _TOKEN_RE.findall(text.casefold())


def field_exact_match(expected: Any, actual: Any) -> bool:
    return normalize_value(expected) == normalize_value(actual)


def token_overlap_f1(expected: Any, actual: Any) -> float:
    """Token-set F1 for string fields.

    Both empty -> 1.0 (correctly agreeing on "no value"). Exactly one empty ->
    0.0. Otherwise harmonic mean of token precision and recall.
    """
    exp = set(tokenize(expected))
    act = set(tokenize(actual))
    if not exp and not act:
        return 1.0
    if not exp or not act:
        return 0.0
    inter = len(exp & act)
    if inter == 0:
        return 0.0
    precision = inter / len(act)
    recall = inter / len(exp)
    return 2 * precision * recall / (precision + recall)


def is_empty(value: Any) -> bool:
    return normalize_value(value) == ""


# --------------------------------------------------------------------------
# Pearson correlation
# --------------------------------------------------------------------------


def pearson_r(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Pearson correlation coefficient. Returns 0.0 for degenerate input.

    If either series has zero variance, correlation is undefined; we return 1.0
    when the series are identical and 0.0 otherwise.
    """
    if len(xs) != len(ys):
        raise ValueError("pearson_r requires equal-length series")
    n = len(xs)
    if n == 0:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return 1.0 if list(xs) == list(ys) else 0.0
    return cov / math.sqrt(var_x * var_y)


# --------------------------------------------------------------------------
# Classification (detection / end-to-end type)
# --------------------------------------------------------------------------


def confusion_matrix(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str] | None = None
) -> dict[str, Any]:
    if len(y_true) != len(y_pred):
        raise ValueError("confusion_matrix requires equal-length series")
    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))
    index = {label: i for i, label in enumerate(labels)}
    size = len(labels)
    matrix = [[0 for _ in range(size)] for _ in range(size)]
    for true, pred in zip(y_true, y_pred):
        if true not in index or pred not in index:
            continue
        matrix[index[true]][index[pred]] += 1
    return {"labels": list(labels), "matrix": matrix}


def _precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def classification_metrics(
    y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str] | None = None
) -> dict[str, Any]:
    """Accuracy, macro-F1, per-class precision/recall/F1 and confusion matrix."""
    if len(y_true) != len(y_pred):
        raise ValueError("classification_metrics requires equal-length series")
    total = len(y_true)
    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))

    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / total if total else 0.0

    per_class: dict[str, dict[str, float]] = {}
    f1_scores: list[float] = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        support = sum(1 for t in y_true if t == label)
        precision, recall, f1 = _precision_recall_f1(tp, fp, fn)
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
        # Macro-F1 averages over classes that appear in the ground truth.
        if support > 0:
            f1_scores.append(f1)

    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "confusion": confusion_matrix(y_true, y_pred, labels),
        "n": total,
    }


# --------------------------------------------------------------------------
# Binary flag (needs_attention)
# --------------------------------------------------------------------------


def binary_flag_metrics(y_true: Sequence[bool], y_pred: Sequence[bool]) -> dict[str, float]:
    """Precision / recall / F1 for the positive (True) class."""
    if len(y_true) != len(y_pred):
        raise ValueError("binary_flag_metrics requires equal-length series")
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if (not t) and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and (not p))
    tn = sum(1 for t, p in zip(y_true, y_pred) if (not t) and (not p))
    precision, recall, f1 = _precision_recall_f1(tp, fp, fn)
    total = len(y_true)
    accuracy = (tp + tn) / total if total else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


# --------------------------------------------------------------------------
# Field extraction
# --------------------------------------------------------------------------


def extraction_metrics(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate field-level extraction quality.

    Each record: {
        "field_keys": [...],          # all extractable keys for the doc type
        "required_fields": [...],
        "expected": {key: value},     # ground truth
        "actual": {key: value},       # model output
    }

    Returns exact-match accuracy (all field instances), mean token-overlap F1
    (over instances where expected and/or actual are non-empty), required-field
    recall, and a per-field error breakdown.
    """
    exact_hits = 0
    exact_total = 0
    f1_sum = 0.0
    f1_count = 0
    req_correct = 0
    req_present = 0

    # field_key -> {"errors": int, "total": int}
    field_breakdown: dict[str, dict[str, int]] = {}

    for record in records:
        field_keys = record.get("field_keys") or []
        required = set(record.get("required_fields") or [])
        expected = record.get("expected") or {}
        actual = record.get("actual") or {}

        for key in field_keys:
            exp_val = expected.get(key, "")
            act_val = actual.get(key, "")
            match = field_exact_match(exp_val, act_val)

            exact_total += 1
            if match:
                exact_hits += 1

            bucket = field_breakdown.setdefault(key, {"errors": 0, "total": 0})
            bucket["total"] += 1
            if not match:
                bucket["errors"] += 1

            if not (is_empty(exp_val) and is_empty(act_val)):
                f1_sum += token_overlap_f1(exp_val, act_val)
                f1_count += 1

            if key in required and not is_empty(exp_val):
                req_present += 1
                if match:
                    req_correct += 1

    return {
        "field_exact_accuracy": exact_hits / exact_total if exact_total else 0.0,
        "field_token_f1": f1_sum / f1_count if f1_count else 0.0,
        "required_field_recall": req_correct / req_present if req_present else 0.0,
        "required_fields_present": req_present,
        "required_fields_correct": req_correct,
        "field_instances": exact_total,
        "field_breakdown": field_breakdown,
    }


# --------------------------------------------------------------------------
# Completeness-score correlation
# --------------------------------------------------------------------------


def completeness_correlation(
    expected_scores: Sequence[float], actual_scores: Sequence[float]
) -> dict[str, Any]:
    r = pearson_r(expected_scores, actual_scores)
    return {"pearson_r": r, "n": len(expected_scores)}
