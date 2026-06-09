"""Configuration, paths, thresholds and database wiring for the eval harness.

All thresholds and pricing are overridable via environment variables so CI and
local runs can tune the gates without code changes.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
GOLDEN_DIR = EVAL_DIR / "golden"
PDFS_DIR = GOLDEN_DIR / "pdfs"
MANIFEST_PATH = GOLDEN_DIR / "manifest.json"
CACHE_DIR = EVAL_DIR / ".cache"
EVAL_DB_PATH = CACHE_DIR / "eval.db"

REPORT_DIR = EVAL_DIR / "report"
REPORT_LATEST_DIR = REPORT_DIR / "latest"


# --------------------------------------------------------------------------
# Doc types (canonical labels) — these are the six prompt types the dataset
# covers, plus the "Other" edge-case label. They must match document_config.
# --------------------------------------------------------------------------

DOC_TYPES = [
    "Gas Safety Certificate",
    "EICR",
    "EPC",
    "Deposit Protection Certificate",
    "Tenancy Agreement",
    "Inventory",
]
OTHER_LABEL = "Other"


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# --------------------------------------------------------------------------
# Thresholds (env-overridable) — the CI gate fails if any is breached.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Thresholds:
    detection_accuracy: float
    required_field_recall: float
    completeness_pearson_r: float
    needs_attention_f1: float


def get_thresholds() -> Thresholds:
    return Thresholds(
        detection_accuracy=_env_float("EVAL_MIN_DETECTION_ACC", 0.90),
        required_field_recall=_env_float("EVAL_MIN_FIELD_RECALL", 0.85),
        completeness_pearson_r=_env_float("EVAL_MIN_COMPLETENESS_R", 0.85),
        needs_attention_f1=_env_float("EVAL_MIN_ATTENTION_F1", 0.80),
    )


# --------------------------------------------------------------------------
# Cost model — Gemini token pricing (USD per 1K tokens), env-overridable.
# Defaults approximate Gemini 2.5 Flash list pricing.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Pricing:
    input_per_1k: float
    output_per_1k: float


def get_pricing() -> Pricing:
    return Pricing(
        input_per_1k=_env_float("EVAL_PRICE_INPUT_PER_1K", 0.0003),
        output_per_1k=_env_float("EVAL_PRICE_OUTPUT_PER_1K", 0.0025),
    )


def default_workers() -> int:
    return _env_int("EVAL_WORKERS", min(8, (os.cpu_count() or 4)))


# --------------------------------------------------------------------------
# Database wiring
# --------------------------------------------------------------------------

_DB_READY = False


def setup_environment(reseed: bool = False) -> str:
    """Create + seed the eval SQLite DB and point the pipeline modules at it.

    Idempotent. Returns the database path. Enables WAL so parallel runners can
    read while the (idempotent) re-seed in document_config serialises writes.
    """
    global _DB_READY

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    db_path = str(EVAL_DB_PATH)
    os.environ["DATABASE_URL"] = db_path

    # Import here so setting DATABASE_URL above is honoured and to avoid a hard
    # import dependency at module load.
    from portal_new import document_config
    import ai_prefill

    # Repoint module-level globals that were captured at import time.
    document_config.DATABASE_URL = db_path
    ai_prefill.DATABASE_URL = db_path

    # Silence the pipeline's per-document logging — under parallel runners it
    # interleaves noisily and adds nothing to the eval output.
    ai_prefill.log = lambda *args, **kwargs: None

    if reseed and EVAL_DB_PATH.exists():
        for suffix in ("", "-wal", "-shm"):
            p = Path(db_path + suffix)
            if p.exists():
                p.unlink()

    if not _DB_READY or reseed:
        # The base document_types table is created by the portal app schema in
        # production; for the standalone eval DB we create a minimal one so
        # document_config's ALTER/seed path can populate the rest.
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS document_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
        document_config.ensure_document_config(db_path)
        _DB_READY = True

    return db_path
