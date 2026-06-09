"""Threshold gate: exit non-zero if any computed metric breaches its threshold.

Reads metric values from a results.json produced by run_eval and compares them
against the *current* environment thresholds (see eval/config.py), so the gate
can be re-run against existing results after tightening a threshold.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from eval import config


def _dig(data: dict[str, Any], *path: str) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _first_available(results: dict[str, Any], candidates: list[tuple[str, ...]]) -> Any:
    tasks = results.get("tasks") or {}
    for path in candidates:
        value = _dig(tasks, *path)
        if value is not None:
            return value
    return None


def build_gates(results: dict[str, Any], thresholds: config.Thresholds | None = None) -> dict[str, Any]:
    thresholds = thresholds or config.get_thresholds()

    specs = [
        (
            "detection_accuracy",
            thresholds.detection_accuracy,
            [("detection", "metrics", "type", "accuracy"),
             ("pipeline", "metrics", "type", "accuracy")],
        ),
        (
            "required_field_recall",
            thresholds.required_field_recall,
            [("extraction", "metrics", "field", "required_field_recall"),
             ("pipeline", "metrics", "field", "required_field_recall")],
        ),
        (
            "completeness_pearson_r",
            thresholds.completeness_pearson_r,
            [("extraction", "metrics", "completeness", "pearson_r"),
             ("pipeline", "metrics", "completeness", "pearson_r")],
        ),
        (
            "needs_attention_f1",
            thresholds.needs_attention_f1,
            [("extraction", "metrics", "needs_attention", "f1"),
             ("pipeline", "metrics", "needs_attention", "f1")],
        ),
    ]

    gates: list[dict[str, Any]] = []
    for name, threshold, candidates in specs:
        value = _first_available(results, candidates)
        if value is None:
            gates.append({"name": name, "threshold": threshold, "value": None,
                          "available": False, "passed": True})
            continue
        passed = float(value) >= float(threshold)
        gates.append({"name": name, "threshold": threshold, "value": float(value),
                      "available": True, "passed": passed})

    overall = all(g["passed"] for g in gates if g["available"])
    return {"gates": gates, "passed": overall}


def format_gates(gate_result: dict[str, Any]) -> str:
    lines = []
    for gate in gate_result["gates"]:
        if not gate["available"]:
            lines.append(f"  - {gate['name']}: (not evaluated)")
            continue
        status = "PASS" if gate["passed"] else "FAIL"
        lines.append(
            f"  [{status}] {gate['name']}: {gate['value']:.4f} "
            f"(threshold >= {gate['threshold']:.2f})"
        )
    lines.append(f"\n  Overall: {'PASS' if gate_result['passed'] else 'FAIL'}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate eval thresholds and gate CI.")
    parser.add_argument(
        "--results",
        type=str,
        default=str(config.REPORT_LATEST_DIR / "results.json"),
        help="Path to results.json (default: eval/report/latest/results.json)",
    )
    args = parser.parse_args()

    path = Path(args.results)
    if not path.is_file():
        print(f"Results file not found: {path}", file=sys.stderr)
        sys.exit(2)

    with path.open("r", encoding="utf-8") as handle:
        results = json.load(handle)

    gate_result = build_gates(results)
    print(format_gates(gate_result))
    sys.exit(0 if gate_result["passed"] else 1)


if __name__ == "__main__":
    main()
