"""End-to-end smoke test: a small offline replay run produces a passing report.

Redirects the dataset/report paths to a temp dir and shrinks the dataset so the
full orchestration (generate -> detect/extract/pipeline -> metrics -> report ->
gate) runs quickly and deterministically.
"""

import pytest

from eval import config, report, run_eval
from eval.golden import generate_golden


@pytest.fixture()
def tiny_dataset(tmp_path, monkeypatch):
    golden = tmp_path / "golden"
    report_dir = tmp_path / "report"
    monkeypatch.setattr(config, "GOLDEN_DIR", golden)
    monkeypatch.setattr(config, "PDFS_DIR", golden / "pdfs")
    monkeypatch.setattr(config, "MANIFEST_PATH", golden / "manifest.json")
    monkeypatch.setattr(config, "REPORT_DIR", report_dir)
    monkeypatch.setattr(config, "REPORT_LATEST_DIR", report_dir / "latest")
    # Small but varied: a few happy cases + one edge per type + one "Other".
    monkeypatch.setattr(generate_golden, "CASES_PER_TYPE", 4)
    monkeypatch.setattr(generate_golden, "OTHER_COUNT", 1)
    monkeypatch.setattr(generate_golden, "EDGE_LAYOUT", {4: "missing_fields"})
    # Loosen thresholds so small-sample noise can't flake the pass assertion.
    for var in ("EVAL_MIN_DETECTION_ACC", "EVAL_MIN_FIELD_RECALL",
                "EVAL_MIN_COMPLETENESS_R", "EVAL_MIN_ATTENTION_F1"):
        monkeypatch.setenv(var, "0.50")
    return tmp_path


def test_replay_run_produces_passing_report(tiny_dataset):
    results = run_eval.run(only=None, live=False, workers=2)

    assert set(results["tasks"]) == {"detection", "extraction", "pipeline"}
    assert results["mode"] == "replay"
    assert results["n_cases"] >= 1
    assert results["passed"] is True
    assert len(results["gates"]) == 4

    html_path = report.write_reports(results)
    assert html_path.is_file()
    assert (config.REPORT_LATEST_DIR / "results.json").is_file()
    assert (config.REPORT_LATEST_DIR / "summary.md").is_file()


def test_only_detection_runs_single_task(tiny_dataset):
    results = run_eval.run(only="detection", live=False, workers=2)
    assert set(results["tasks"]) == {"detection"}
    # Extraction-backed gates should be reported as not-evaluated, not failing.
    recall_gate = next(g for g in results["gates"] if g["name"] == "required_field_recall")
    assert recall_gate["available"] is False
    assert results["passed"] is True
