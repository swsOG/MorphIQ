"""Report generation: JSON + Markdown + self-contained HTML.

The HTML embeds a confusion-matrix heatmap (matplotlib, base64 PNG), a
per-case pass/fail table with expected-vs-actual JSON diffs, a field-level
error breakdown and a cost summary. Outputs land in eval/report/latest/ plus a
timestamped archive directory.
"""

from __future__ import annotations

import base64
import io
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval import config
from eval.metrics import field_exact_match, is_empty

# --------------------------------------------------------------------------
# Cost
# --------------------------------------------------------------------------


def compute_cost(total_tokens_prompt: int, total_tokens_output: int) -> float:
    pricing = config.get_pricing()
    return round(
        (total_tokens_prompt / 1000.0) * pricing.input_per_1k
        + (total_tokens_output / 1000.0) * pricing.output_per_1k,
        6,
    )


# --------------------------------------------------------------------------
# Confusion-matrix heatmap
# --------------------------------------------------------------------------


def confusion_png_base64(confusion: dict[str, Any]) -> str | None:
    labels = confusion.get("labels") or []
    matrix = confusion.get("matrix") or []
    if not labels or not matrix:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(1.4 + 0.7 * len(labels), 1.2 + 0.6 * len(labels)))
    im = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Detection confusion matrix")
    for i in range(len(labels)):
        for j in range(len(labels)):
            val = matrix[i][j]
            if val:
                ax.text(j, i, str(val), ha="center", va="center", fontsize=8,
                        color="white" if val > (max(max(r) for r in matrix) / 2) else "black")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# --------------------------------------------------------------------------
# Per-case helpers
# --------------------------------------------------------------------------


def _case_passed(record: dict[str, Any]) -> bool:
    expected = record.get("expected") or {}
    actual = record.get("actual") or {}
    for key in record.get("required_fields") or []:
        exp = expected.get(key, "")
        if is_empty(exp):
            continue
        if not field_exact_match(exp, actual.get(key, "")):
            return False
    return True


# --------------------------------------------------------------------------
# Markdown summary (also used as the PR comment body)
# --------------------------------------------------------------------------


def render_markdown(results: dict[str, Any]) -> str:
    lines: list[str] = []
    status = "✅ PASS" if results.get("passed") else "❌ FAIL"
    lines.append(f"## MorphIQ Eval — {status}")
    lines.append("")
    lines.append(f"- Mode: `{results.get('mode')}`  ·  Cases: {results.get('n_cases')}  "
                 f"·  Generated: {results.get('generated_at')}")
    cost = results.get("cost") or {}
    lines.append(f"- Tokens: {cost.get('total_tokens', 0):,}  ·  "
                 f"Est. cost: ${cost.get('usd', 0):.4f} ({results.get('mode')})")
    lines.append("")
    lines.append("| Gate | Value | Threshold | Result |")
    lines.append("|------|-------|-----------|--------|")
    for gate in results.get("gates", []):
        if not gate["available"]:
            lines.append(f"| {gate['name']} | – | {gate['threshold']:.2f} | not evaluated |")
            continue
        emoji = "✅" if gate["passed"] else "❌"
        lines.append(f"| {gate['name']} | {gate['value']:.4f} | "
                     f"{gate['threshold']:.2f} | {emoji} |")
    lines.append("")

    tasks = results.get("tasks") or {}
    if "pipeline" in tasks:
        pa = tasks["pipeline"]["metrics"].get("pipeline_accuracy")
        if pa is not None:
            lines.append(f"End-to-end pipeline accuracy: **{pa:.4f}**")
            lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MorphIQ Eval Report</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; background:#f5f6f8; color:#1c1e21; }
  header { background:#0f172a; color:#fff; padding:20px 32px; }
  header h1 { margin:0; font-size:20px; }
  header .meta { color:#94a3b8; font-size:13px; margin-top:6px; }
  main { padding: 24px 32px; max-width: 1200px; margin: 0 auto; }
  .cards { display:flex; flex-wrap:wrap; gap:14px; margin-bottom:24px; }
  .card { background:#fff; border-radius:10px; padding:16px 18px; flex:1 1 200px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
  .card .label { font-size:12px; text-transform:uppercase; letter-spacing:.04em; color:#64748b; }
  .card .value { font-size:24px; font-weight:700; margin-top:4px; }
  .pass { color:#15803d; } .fail { color:#b91c1c; }
  .badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:600; }
  .badge.pass { background:#dcfce7; } .badge.fail { background:#fee2e2; }
  section { background:#fff; border-radius:10px; padding:18px 20px; margin-bottom:22px; box-shadow:0 1px 3px rgba(0,0,0,.06); }
  section h2 { font-size:15px; margin:0 0 14px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th, td { text-align:left; padding:7px 10px; border-bottom:1px solid #eceef1; }
  th { color:#475569; font-weight:600; }
  tr.failrow { background:#fff7f7; }
  .diff { display:flex; gap:12px; }
  .diff pre { flex:1; background:#0f172a; color:#e2e8f0; padding:10px; border-radius:8px; overflow:auto; font-size:11px; max-height:240px; }
  details { margin-top:6px; }
  summary { cursor:pointer; color:#2563eb; font-size:12px; }
  img.heatmap { max-width:100%; height:auto; }
  .pill { font-size:11px; color:#64748b; }
</style>
</head>
<body>
<header>
  <h1>MorphIQ LLM Eval Report &nbsp; <span class="badge {{ overall_class }}">{{ overall_text }}</span></h1>
  <div class="meta">Mode: {{ mode }} · {{ n_cases }} cases · {{ generated_at }}</div>
</header>
<main>
  <div class="cards">
    {% for gate in gates %}
    <div class="card">
      <div class="label">{{ gate.name }}</div>
      {% if gate.available %}
      <div class="value {{ 'pass' if gate.passed else 'fail' }}">{{ '%.3f'|format(gate.value) }}</div>
      <div class="pill">threshold ≥ {{ '%.2f'|format(gate.threshold) }}</div>
      {% else %}
      <div class="value">–</div><div class="pill">not evaluated</div>
      {% endif %}
    </div>
    {% endfor %}
    <div class="card">
      <div class="label">Est. cost ({{ mode }})</div>
      <div class="value">${{ '%.4f'|format(cost_usd) }}</div>
      <div class="pill">{{ '{:,}'.format(total_tokens) }} tokens</div>
    </div>
  </div>

  {% if heatmap %}
  <section>
    <h2>Detection</h2>
    <img class="heatmap" src="data:image/png;base64,{{ heatmap }}" alt="confusion matrix">
    {% if per_class %}
    <table>
      <thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead>
      <tbody>
      {% for label, m in per_class.items() %}
        <tr><td>{{ label }}</td><td>{{ '%.3f'|format(m.precision) }}</td>
        <td>{{ '%.3f'|format(m.recall) }}</td><td>{{ '%.3f'|format(m.f1) }}</td>
        <td>{{ m.support }}</td></tr>
      {% endfor %}
      </tbody>
    </table>
    {% endif %}
  </section>
  {% endif %}

  {% if field_breakdown %}
  <section>
    <h2>Field-level error breakdown</h2>
    <table>
      <thead><tr><th>Field</th><th>Errors</th><th>Instances</th><th>Error rate</th></tr></thead>
      <tbody>
      {% for f in field_breakdown %}
        <tr><td>{{ f.field }}</td><td>{{ f.errors }}</td><td>{{ f.total }}</td>
        <td>{{ '%.1f'|format(f.rate * 100) }}%</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </section>
  {% endif %}

  {% if cases %}
  <section>
    <h2>Per-case results ({{ cases|length }})</h2>
    <table>
      <thead><tr><th>Case</th><th>Edge</th><th>Completeness (exp/act)</th>
      <th>Attention (exp/act)</th><th>Status</th></tr></thead>
      <tbody>
      {% for c in cases %}
        <tr class="{{ 'failrow' if not c.passed else '' }}">
          <td>{{ c.id }}</td>
          <td>{{ c.edge_case or '—' }}</td>
          <td>{{ c.expected_completeness }} / {{ c.actual_completeness }}</td>
          <td>{{ c.expected_attention }} / {{ c.actual_attention }}</td>
          <td class="{{ 'pass' if c.passed else 'fail' }}">{{ 'PASS' if c.passed else 'FAIL' }}
            {% if not c.passed %}
            <details><summary>diff</summary>
              <div class="diff">
                <pre>expected
{{ c.expected_json }}</pre>
                <pre>actual
{{ c.actual_json }}</pre>
              </div>
            </details>
            {% endif %}
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </section>
  {% endif %}
</main>
</body>
</html>
"""


def render_html(results: dict[str, Any]) -> str:
    from jinja2 import Template

    tasks = results.get("tasks") or {}

    # Confusion matrix from detection (preferred) or pipeline.
    confusion = (
        _safe(tasks, "detection", "metrics", "type", "confusion")
        or _safe(tasks, "pipeline", "metrics", "type", "confusion")
    )
    heatmap = confusion_png_base64(confusion) if confusion else None
    per_class = (
        _safe(tasks, "detection", "metrics", "type", "per_class")
        or _safe(tasks, "pipeline", "metrics", "type", "per_class")
    )

    # Field breakdown from extraction (preferred) or pipeline.
    breakdown_raw = (
        _safe(tasks, "extraction", "metrics", "field", "field_breakdown")
        or _safe(tasks, "pipeline", "metrics", "field", "field_breakdown")
        or {}
    )
    field_breakdown = sorted(
        (
            {"field": k, "errors": v["errors"], "total": v["total"],
             "rate": (v["errors"] / v["total"]) if v["total"] else 0.0}
            for k, v in breakdown_raw.items()
        ),
        key=lambda r: r["rate"],
        reverse=True,
    )

    # Per-case table from extraction (preferred) or pipeline.
    case_records = (
        _safe(tasks, "extraction", "cases")
        or _safe(tasks, "pipeline", "cases")
        or []
    )
    cases = []
    for rec in case_records:
        passed = _case_passed(rec)
        cases.append(
            {
                "id": rec.get("id"),
                "edge_case": rec.get("edge_case"),
                "expected_completeness": rec.get("expected_completeness"),
                "actual_completeness": rec.get("actual_completeness"),
                "expected_attention": rec.get("expected_attention"),
                "actual_attention": rec.get("actual_attention"),
                "passed": passed,
                "expected_json": json.dumps(rec.get("expected") or {}, indent=2, ensure_ascii=False),
                "actual_json": json.dumps(rec.get("actual") or {}, indent=2, ensure_ascii=False),
            }
        )
    # Show failures first.
    cases.sort(key=lambda c: (c["passed"], c["id"]))

    cost = results.get("cost") or {}
    template = Template(_HTML_TEMPLATE)
    return template.render(
        overall_class="pass" if results.get("passed") else "fail",
        overall_text="PASS" if results.get("passed") else "FAIL",
        mode=results.get("mode"),
        n_cases=results.get("n_cases"),
        generated_at=results.get("generated_at"),
        gates=results.get("gates", []),
        cost_usd=cost.get("usd", 0.0),
        total_tokens=cost.get("total_tokens", 0),
        heatmap=heatmap,
        per_class=per_class,
        field_breakdown=field_breakdown,
        cases=cases,
    )


def _safe(data: dict[str, Any], *path: str) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


# --------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------


def write_reports(results: dict[str, Any]) -> Path:
    """Write results.json, summary.md and index.html. Returns the HTML path."""
    config.REPORT_LATEST_DIR.mkdir(parents=True, exist_ok=True)

    results_json = json.dumps(results, indent=2, ensure_ascii=False)
    markdown = render_markdown(results)
    html = render_html(results)

    (config.REPORT_LATEST_DIR / "results.json").write_text(results_json, encoding="utf-8")
    (config.REPORT_LATEST_DIR / "summary.md").write_text(markdown, encoding="utf-8")
    html_path = config.REPORT_LATEST_DIR / "index.html"
    html_path.write_text(html, encoding="utf-8")

    # Timestamped archive.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = config.REPORT_DIR / stamp
    archive.mkdir(parents=True, exist_ok=True)
    for name in ("results.json", "summary.md", "index.html"):
        shutil.copyfile(config.REPORT_LATEST_DIR / name, archive / name)

    return html_path
