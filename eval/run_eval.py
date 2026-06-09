"""CLI entry point for the MorphIQ evaluation harness.

    python -m eval.run_eval [--only detection|extraction|pipeline]
                            [--live] [--workers N] [--no-report] [--reseed]

By default runs detection + extraction + pipeline over the golden dataset using
recorded responses (offline, deterministic), computes metrics, writes the
report and exits non-zero if any threshold gate is breached. ``--live`` swaps in
the real Gemini client to measure the actual model.
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable

from eval import config, metrics, report
from eval.ci_gate import build_gates, format_gates
from eval.clients import LiveClient, ReplayClient, summarize_usage
from eval.dataset import GoldenCase, load_cases, missing_pdfs
from eval.runners import detection as detection_runner
from eval.runners import extraction as extraction_runner
from eval.runners import pipeline as pipeline_runner

ALL_TASKS = ("detection", "extraction", "pipeline")


def _ensure_dataset() -> list[GoldenCase]:
    need_build = not config.MANIFEST_PATH.exists()
    cases: list[GoldenCase] = []
    if not need_build:
        cases = load_cases()
        need_build = bool(missing_pdfs(cases))
    if need_build:
        print("Golden PDFs missing — building dataset...")
        from eval.golden.generate_golden import build_dataset

        build_dataset()
        cases = load_cases()
    return cases


def _run_task(
    run_case: Callable[[GoldenCase, Any], dict[str, Any]],
    cases: list[GoldenCase],
    make_client: Callable[[GoldenCase], Any],
    workers: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [None] * len(cases)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_case, case, make_client(case)): idx
            for idx, case in enumerate(cases)
        }
        for future in as_completed(futures):
            out[futures[future]] = future.result()
    return out


def _extraction_field_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "field_keys": r["field_keys"],
            "required_fields": r["required_fields"],
            "expected": r["expected"],
            "actual": r["actual"],
        }
        for r in records
    ]


def _field_and_quality_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    field = metrics.extraction_metrics(_extraction_field_records(records))
    completeness = metrics.completeness_correlation(
        [r["expected_completeness"] for r in records],
        [r["actual_completeness"] for r in records],
    )
    attention = metrics.binary_flag_metrics(
        [r["expected_attention"] for r in records],
        [r["actual_attention"] for r in records],
    )
    return {"field": field, "completeness": completeness, "needs_attention": attention}


def _all_usages(tasks: dict[str, Any]) -> list[dict[str, int]]:
    usages: list[dict[str, int]] = []
    for task in tasks.values():
        for rec in task.get("cases", []):
            usages.extend(rec.get("usage") or [])
    return usages


def run(only: str | None, live: bool, workers: int) -> dict[str, Any]:
    config.setup_environment()
    cases = _ensure_dataset()

    def make_client(case: GoldenCase) -> Any:
        return LiveClient() if live else ReplayClient(case.recording)

    selected = (only,) if only else ALL_TASKS
    tasks: dict[str, Any] = {}

    if "detection" in selected:
        records = _run_task(detection_runner.run_case, cases, make_client, workers)
        y_true = [r["expected"] for r in records]
        y_pred = [r["predicted"] for r in records]
        tasks["detection"] = {
            "metrics": {"type": metrics.classification_metrics(y_true, y_pred)},
            "cases": records,
        }

    if "extraction" in selected:
        records = _run_task(extraction_runner.run_case, cases, make_client, workers)
        tasks["extraction"] = {"metrics": _field_and_quality_metrics(records), "cases": records}

    if "pipeline" in selected:
        records = _run_task(pipeline_runner.run_case, cases, make_client, workers)
        y_true = [r["expected_type"] for r in records]
        y_pred = [r["predicted_type"] for r in records]
        pipeline_metrics = _field_and_quality_metrics(records)
        pipeline_metrics["type"] = metrics.classification_metrics(y_true, y_pred)
        pipeline_metrics["pipeline_accuracy"] = (
            sum(1 for r in records if r["pipeline_correct"]) / len(records) if records else 0.0
        )
        tasks["pipeline"] = {"metrics": pipeline_metrics, "cases": records}

    usage_summary = summarize_usage(_all_usages(tasks))
    cost_usd = report.compute_cost(usage_summary["prompt_tokens"], usage_summary["output_tokens"])

    results: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if live else "replay",
        "n_cases": len(cases),
        "tasks": tasks,
        "thresholds": vars(config.get_thresholds()),
        "cost": {**usage_summary, "usd": cost_usd},
    }
    gate_result = build_gates(results)
    results["gates"] = gate_result["gates"]
    results["passed"] = gate_result["passed"]
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MorphIQ LLM eval harness.")
    parser.add_argument("--only", choices=ALL_TASKS, help="Run a single task only.")
    parser.add_argument("--live", action="store_true",
                        help="Call the real Gemini API instead of recorded responses.")
    parser.add_argument("--workers", type=int, default=config.default_workers(),
                        help="Parallel worker threads (default: env EVAL_WORKERS or CPU count).")
    parser.add_argument("--no-report", action="store_true", help="Skip writing the report.")
    parser.add_argument("--reseed", action="store_true",
                        help="Rebuild the eval config database before running.")
    args = parser.parse_args()

    if args.reseed:
        config.setup_environment(reseed=True)

    results = run(only=args.only, live=args.live, workers=max(1, args.workers))

    if not args.no_report:
        html_path = report.write_reports(results)
        print(f"\nReport: {html_path}")

    print("\n" + format_gates({"gates": results["gates"], "passed": results["passed"]}))
    cost = results["cost"]
    print(f"\n  Tokens: {cost['total_tokens']:,}  ·  Est. cost ({results['mode']}): ${cost['usd']:.4f}")
    sys.exit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
