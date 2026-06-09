"""Tests for the threshold gate logic."""

from eval import config
from eval import ci_gate


def _results_with(detection_acc, recall, pearson, attention_f1):
    return {
        "tasks": {
            "detection": {"metrics": {"type": {"accuracy": detection_acc}}},
            "extraction": {
                "metrics": {
                    "field": {"required_field_recall": recall},
                    "completeness": {"pearson_r": pearson},
                    "needs_attention": {"f1": attention_f1},
                }
            },
        }
    }


def test_all_gates_pass_above_thresholds():
    results = _results_with(0.95, 0.90, 0.92, 0.88)
    out = ci_gate.build_gates(results, config.Thresholds(0.90, 0.85, 0.85, 0.80))
    assert out["passed"]
    assert all(g["passed"] for g in out["gates"])


def test_single_breach_fails_overall():
    results = _results_with(0.95, 0.84, 0.92, 0.88)  # recall below 0.85
    out = ci_gate.build_gates(results, config.Thresholds(0.90, 0.85, 0.85, 0.80))
    assert not out["passed"]
    recall_gate = next(g for g in out["gates"] if g["name"] == "required_field_recall")
    assert not recall_gate["passed"]


def test_boundary_value_passes():
    # Exactly at threshold counts as passing (>=).
    results = _results_with(0.90, 0.85, 0.85, 0.80)
    out = ci_gate.build_gates(results, config.Thresholds(0.90, 0.85, 0.85, 0.80))
    assert out["passed"]


def test_missing_metric_is_not_evaluated_and_does_not_fail():
    # Only detection present (e.g. --only detection).
    results = {"tasks": {"detection": {"metrics": {"type": {"accuracy": 0.95}}}}}
    out = ci_gate.build_gates(results, config.Thresholds(0.90, 0.85, 0.85, 0.80))
    assert out["passed"]
    recall_gate = next(g for g in out["gates"] if g["name"] == "required_field_recall")
    assert recall_gate["available"] is False


def test_pipeline_metrics_used_as_fallback():
    # When extraction is absent, pipeline metrics back the gates.
    results = {
        "tasks": {
            "pipeline": {
                "metrics": {
                    "type": {"accuracy": 0.93},
                    "field": {"required_field_recall": 0.88},
                    "completeness": {"pearson_r": 0.9},
                    "needs_attention": {"f1": 0.85},
                }
            }
        }
    }
    out = ci_gate.build_gates(results, config.Thresholds(0.90, 0.85, 0.85, 0.80))
    assert out["passed"]
    assert all(g["available"] for g in out["gates"])
