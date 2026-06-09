"""Unit tests for the pure metric functions in eval/metrics.py."""

import math

import pytest

from eval import metrics


def test_normalize_and_exact_match():
    assert metrics.normalize_value("  Pass  ") == "pass"
    assert metrics.field_exact_match("PASS", "pass")
    assert metrics.field_exact_match("A B", "a   b")
    assert not metrics.field_exact_match("Pass", "Pxss")


def test_token_overlap_f1():
    assert metrics.token_overlap_f1("", "") == 1.0
    assert metrics.token_overlap_f1("abc", "") == 0.0
    assert metrics.token_overlap_f1("a b c", "a b c") == 1.0
    # Drop one of two tokens -> precision 1, recall 0.5 -> F1 = 2/3.
    assert math.isclose(metrics.token_overlap_f1("john smith", "john"), 2 / 3, rel_tol=1e-9)
    assert metrics.token_overlap_f1("alpha", "beta") == 0.0


def test_pearson_r_basic():
    assert math.isclose(metrics.pearson_r([1, 2, 3], [2, 4, 6]), 1.0, rel_tol=1e-9)
    assert math.isclose(metrics.pearson_r([1, 2, 3], [6, 4, 2]), -1.0, rel_tol=1e-9)
    # Zero variance + identical -> 1.0; zero variance + different -> 0.0.
    assert metrics.pearson_r([5, 5, 5], [5, 5, 5]) == 1.0
    assert metrics.pearson_r([5, 5, 5], [1, 2, 3]) == 0.0


def test_pearson_r_length_mismatch():
    with pytest.raises(ValueError):
        metrics.pearson_r([1, 2], [1])


def test_classification_metrics_perfect():
    y = ["A", "B", "A", "C"]
    out = metrics.classification_metrics(y, y, labels=["A", "B", "C"])
    assert out["accuracy"] == 1.0
    assert out["macro_f1"] == 1.0
    assert out["per_class"]["A"]["support"] == 2


def test_classification_metrics_with_errors():
    y_true = ["A", "A", "B", "B"]
    y_pred = ["A", "B", "B", "B"]
    out = metrics.classification_metrics(y_true, y_pred, labels=["A", "B"])
    assert out["accuracy"] == 0.75
    # Confusion matrix: A row -> [1 correct, 1 -> B]; B row -> [0, 2].
    cm = out["confusion"]
    a, b = cm["labels"].index("A"), cm["labels"].index("B")
    assert cm["matrix"][a][a] == 1
    assert cm["matrix"][a][b] == 1
    assert cm["matrix"][b][b] == 2


def test_binary_flag_metrics():
    y_true = [True, True, False, False]
    y_pred = [True, False, True, False]
    out = metrics.binary_flag_metrics(y_true, y_pred)
    assert out["tp"] == 1 and out["fp"] == 1 and out["fn"] == 1 and out["tn"] == 1
    assert out["precision"] == 0.5
    assert out["recall"] == 0.5
    assert out["f1"] == 0.5
    assert out["accuracy"] == 0.5


def test_extraction_metrics():
    records = [
        {
            "field_keys": ["a", "b", "c"],
            "required_fields": ["a", "b"],
            "expected": {"a": "x", "b": "y", "c": ""},
            "actual": {"a": "x", "b": "WRONG", "c": ""},
        }
    ]
    out = metrics.extraction_metrics(records)
    # 3 field instances: a matches, b mismatches, c both empty (match) -> 2/3.
    assert math.isclose(out["field_exact_accuracy"], 2 / 3, rel_tol=1e-9)
    # Required present = a, b (both non-empty in expected); only a correct -> 0.5.
    assert out["required_fields_present"] == 2
    assert out["required_fields_correct"] == 1
    assert out["required_field_recall"] == 0.5
    assert out["field_breakdown"]["b"]["errors"] == 1


def test_completeness_correlation():
    out = metrics.completeness_correlation([100, 50, 0], [90, 40, 10])
    assert out["n"] == 3
    assert out["pearson_r"] > 0.9
