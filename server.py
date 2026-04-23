"""
ScanStation Local API Server
====================================================================

Lightweight local server that lets the browser UI trigger actions
like exporting documents without needing to open CMD.

RUNS ON: http://127.0.0.1:8765 (localhost only — not exposed to network)

ENDPOINTS:
  GET  /health              → Check if server is running
  GET  /clients             → List all client folders
  POST /export              → Export verified docs for a client
                               Body: { "client": "TestClient" }
  GET  /stats/<client>      → Get document counts for a client
  GET  /docs/<client>       → List all documents for a client (review.json data + counts)
  POST /review/<client>/<doc_id>  → Save review data to review.json
  GET  /pdf/<client>/<doc_id>    → Serve PDF file for preview

HOW TO USE:
  This runs automatically via Start_System_v2.bat
  Or manually: python server.py

DEPENDENCIES:
  pip install flask flask-cors
"""

import json
import os
import sqlite3
import threading
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime, UTC
from urllib.parse import quote
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pdfminer.high_level import extract_text
from pypdf import PdfReader, PdfWriter

from export_client import run_export
from sync_to_portal import sync_portal_for_clients, sync_single_doc
from portal_new import document_config

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────

# Filesystem root: same folder as this script (contains Clients/, Templates/).
# Override with MORPHIQ_BASE or SCANSTATION_BASE env vars.
_base_env = (os.environ.get("MORPHIQ_BASE") or os.environ.get("SCANSTATION_BASE") or "").strip()
BASE = Path(_base_env).resolve() if _base_env else Path(__file__).resolve().parent
HOST = "127.0.0.1"  # Localhost only — never exposed to network
PORT = 8765

app = Flask(__name__)

# Allow requests from file:// origins (browsers send Origin: null for local HTML files)
CORS(app, origins=["null"], supports_credentials=False)

# Track if an export is currently running (prevent double-clicks)
export_lock = threading.Lock()

# Map doc_type display name to template file stem for rescan empty fields
DOC_TYPE_TO_TEMPLATE = {
    "tenancy agreement": "tenancy_agreement",
    "gas safety certificate": "gas_safety_certificate",
    "gas safety (cp12)": "gas_safety_certificate",
    "eicr": "eicr",
    "epc": "epc",
    "general document": "general_document",
}

ALLOWED_RAW_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".pdf"}


# ──────────────────────────────────────────────
# HELPERS — merge / split
# ──────────────────────────────────────────────

def _get_next_doc_id(batch_folder: Path) -> str:
    """Return the next sequential DOC-XXXXX identifier inside a batch folder."""
    existing = []
    if batch_folder.exists():
        for item in batch_folder.iterdir():
            if item.is_dir() and item.name.startswith("DOC-"):
                try:
                    num = int(item.name.split("-")[1])
                    existing.append(num)
                except (IndexError, ValueError):
                    pass
    return f"DOC-{max(existing, default=0) + 1:05d}"


def _run_ai_prefill(doc_folder: Path) -> None:
    """Best-effort subprocess call to ai_prefill.py for a DOC folder."""
    script = BASE / "ai_prefill.py"
    if not script.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(script), str(doc_folder)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
        )
    except Exception as e:
        app.logger.warning(f"AI prefill error for {doc_folder.name}: {e}")


def _clients_dir() -> Path:
    return BASE / "Clients"


def _client_dir(client_name: str) -> Path:
    return _clients_dir() / client_name


def _raw_dir(client_name: str) -> Path:
    raw_dir = _client_dir(client_name) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir


def _sanitize_raw_filename(filename: str) -> str:
    ext = (Path(filename or "").suffix or "").lower()
    if ext not in ALLOWED_RAW_EXTENSIONS:
        ext = ".jpg"
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    rand = os.urandom(2).hex()
    return f"scan_{ts}_{rand}{ext}"


def _write_raw_meta(raw_dir: Path, raw_name: str, meta: dict) -> None:
    meta_path = raw_dir / f"{raw_name}.meta.json"
    with meta_path.open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, ensure_ascii=False)


def _remove_doc_from_portal(client_name: str, doc_id: str) -> None:
    """Delete a document and its fields from portal.db by source_doc_id."""
    db_path = str(BASE / "portal.db")
    if not os.path.isfile(db_path):
        return
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id FROM clients WHERE name = ?", (client_name,)
        ).fetchone()
        if not row:
            return
        client_id = row["id"]
        doc_row = conn.execute(
            "SELECT id FROM documents WHERE source_doc_id = ? AND client_id = ?",
            (doc_id, client_id),
        ).fetchone()
        if not doc_row:
            return
        document_id = doc_row["id"]
        conn.execute("DELETE FROM document_fields WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.execute(
            """DELETE FROM properties WHERE id NOT IN (
                   SELECT DISTINCT property_id FROM documents WHERE property_id IS NOT NULL
               )"""
        )
        conn.commit()
    finally:
        conn.close()


def _find_pdf(doc_folder: Path) -> Path | None:
    """Return the first PDF file inside a DOC folder, or None."""
    for f in doc_folder.iterdir():
        if f.is_file() and f.suffix.lower() == ".pdf":
            return f
    return None


# ──────────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Check if the server is running."""
    return jsonify({"status": "ok", "server": "ScanStation API", "port": PORT})


@app.route("/clients", methods=["GET"])
def list_clients():
    """List all client folders."""
    clients_dir = _clients_dir()
    if not clients_dir.exists():
        return jsonify({"clients": []})

    clients = [
        d.name for d in sorted(clients_dir.iterdir())
        if d.is_dir()
    ]
    return jsonify({"clients": clients})


@app.route("/station-config", methods=["GET"])
def station_config():
    """Expose backend-driven station settings to keep UI and pipeline aligned."""
    database_url = os.environ.get("DATABASE_URL", str(BASE / "portal.db"))
    configs = document_config.get_document_configs(database_url)
    return jsonify(
        {
            "base_path": str(BASE),
            "clients_path": str(_clients_dir()),
            "allowed_upload_extensions": sorted(ALLOWED_RAW_EXTENSIONS),
            "document_types": [
                {
                    "label": config["label"],
                    "document_key": config["document_key"],
                    "required_fields": config["required_fields"],
                    "field_definitions": config["extraction_fields"],
                    "show_in_upload": config["show_in_upload"],
                    "show_in_detection": config["show_in_detection"],
                }
                for config in configs
            ],
        }
    )


@app.route("/intake/<client_name>", methods=["POST"])
def intake_file(client_name: str):
    """
    Accept a scanned/imported file and write it into the canonical raw folder that
    the watcher and review pipeline already use.
    """
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"success": False, "error": "No file provided"}), 400

    ext = (Path(upload.filename).suffix or "").lower()
    if ext not in ALLOWED_RAW_EXTENSIONS:
        return jsonify({"success": False, "error": f"Unsupported file type: {ext or 'unknown'}"}), 400

    raw_dir = _raw_dir(client_name)
    raw_name = _sanitize_raw_filename(upload.filename)
    raw_path = raw_dir / raw_name

    try:
        upload.save(str(raw_path))
    except Exception as exc:
        return jsonify({"success": False, "error": f"Failed to save upload: {exc}"}), 500

    meta = {
        "doc_name": (request.form.get("doc_name") or "").strip() or None,
        "property_address": (request.form.get("property_address") or "").strip() or None,
    }
    group_id = (request.form.get("group_id") or "").strip()
    if group_id:
        meta["group_id"] = group_id
    for key in ("page_number", "total_pages_so_far"):
        raw_value = (request.form.get(key) or "").strip()
        if raw_value:
            try:
                meta[key] = int(raw_value)
            except ValueError:
                meta[key] = raw_value

    try:
        _write_raw_meta(raw_dir, raw_name, meta)
    except Exception as exc:
        try:
            if raw_path.exists():
                raw_path.unlink()
        except Exception:
            pass
        return jsonify({"success": False, "error": f"Failed to save metadata: {exc}"}), 500

    return jsonify(
        {
            "success": True,
            "client": client_name,
            "raw_name": raw_name,
            "raw_path": str(raw_path),
            "kind": "pdf" if ext == ".pdf" else "image",
        }
    )


@app.route("/raw-meta/<client_name>/<raw_name>", methods=["POST"])
def update_raw_meta(client_name: str, raw_name: str):
    """Update the sidecar metadata for a raw file already saved in canonical intake."""
    raw_dir = _raw_dir(client_name)
    raw_path = raw_dir / raw_name
    if not raw_path.exists():
        return jsonify({"success": False, "error": "Raw file not found"}), 404

    payload = request.get_json(silent=True) or {}
    meta = {
        "doc_name": (payload.get("doc_name") or "").strip() or None,
        "property_address": (payload.get("property_address") or "").strip() or None,
    }
    if payload.get("group_id"):
        meta["group_id"] = str(payload["group_id"]).strip()
    for key in ("page_number", "total_pages_so_far"):
        if payload.get(key) is not None:
            meta[key] = payload[key]
    try:
        _write_raw_meta(raw_dir, raw_name, meta)
    except Exception as exc:
        return jsonify({"success": False, "error": f"Failed to update metadata: {exc}"}), 500
    return jsonify({"success": True, "raw_name": raw_name})


@app.route("/raw-group-complete/<client_name>/<group_id>", methods=["POST"])
def mark_raw_group_complete(client_name: str, group_id: str):
    raw_dir = _raw_dir(client_name)
    marker_path = raw_dir / f"{group_id}.group_complete"
    try:
        marker_path.write_text("", encoding="utf-8")
    except Exception as exc:
        return jsonify({"success": False, "error": f"Failed to mark group complete: {exc}"}), 500
    return jsonify({"success": True, "group_id": group_id})


@app.route("/export", methods=["POST"])
def export():
    """Export verified documents for a client."""
    # Parse request
    data = request.get_json(silent=True)
    if not data or not data.get("client"):
        return jsonify({"success": False, "error": "Missing 'client' in request body"}), 400

    client_name = data["client"].strip()

    # Validate client exists
    client_dir = BASE / "Clients" / client_name
    if not client_dir.exists():
        return jsonify({"success": False, "error": f"Client folder not found: {client_name}"}), 404

    # Prevent concurrent exports
    if not export_lock.acquire(blocking=False):
        return jsonify({"success": False, "error": "An export is already running. Please wait."}), 409

    try:
        result = run_export(client_name)
        if result.get("success"):
            # Keep the portal database in sync automatically for this client
            try:
                sync_summary = sync_portal_for_clients([client_name])
                result["portal_sync"] = sync_summary
            except Exception as sync_err:
                # Don't fail the export if sync has an issue; just report it.
                result["portal_sync_error"] = str(sync_err)

            # After export, open the new MorphIQ portal (portal_new) instead of the legacy viewer.html
            # The client name is passed as a query param for potential filtering, but the portal
            # will still work even if it ignores this parameter.
            result["viewer_url"] = f"http://127.0.0.1:5000/?client={quote(client_name)}"
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": f"Server error: {e}"}), 500
    finally:
        export_lock.release()


@app.route("/open-folder", methods=["POST"])
def open_folder():
    """Open a folder in the system file manager (e.g. Explorer). Path must be under BASE."""
    data = request.get_json(silent=True)
    if not data or not data.get("path"):
        return jsonify({"success": False, "error": "Missing 'path' in request body"}), 400

    raw = data["path"].strip()
    try:
        folder = Path(raw).resolve()
        base = BASE.resolve()
        if not folder.is_dir():
            return jsonify({"success": False, "error": "Path is not a folder"}), 400
        try:
            folder.relative_to(base)
        except ValueError:
            return jsonify({"success": False, "error": "Path must be inside the ScanSystem folder"}), 400
        if sys.platform == "win32":
            os.startfile(str(folder))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(folder)], check=False)
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/delivery/<client_name>/<export_folder>/", defaults={"filepath": ""})
@app.route("/delivery/<client_name>/<export_folder>/<path:filepath>")
def serve_delivery(client_name: str, export_folder: str, filepath: str):
    """Serve files from a client's Delivery folder so the viewer can load over HTTP (enables PDF search highlighting)."""
    root = BASE / "Clients" / client_name / "Exports" / export_folder
    root = root.resolve()
    try:
        root.relative_to(BASE.resolve())
    except ValueError:
        return jsonify({"error": "Invalid path"}), 404
    if not root.is_dir():
        return jsonify({"error": "Delivery folder not found"}), 404
    if not filepath:
        return jsonify({"error": "Specify a file path"}), 404
    full = (root / filepath).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        return jsonify({"error": "Invalid path"}), 404
    if full.is_dir() or not full.is_file():
        return jsonify({"error": "Not found"}), 404
    return send_file(full, as_attachment=False, download_name=full.name)


@app.route("/stats/<client_name>", methods=["GET"])
def client_stats(client_name: str):
    """Get document counts for a client (total, verified, new, needs review, failed)."""
    batches_path = BASE / "Clients" / client_name / "Batches"

    if not batches_path.exists():
        return jsonify({"error": f"Client not found: {client_name}"}), 404

    counts = {"total": 0, "New": 0, "Verified": 0, "Needs Review": 0, "Failed": 0}

    for date_folder in batches_path.iterdir():
        if not date_folder.is_dir():
            continue
        for doc_folder in date_folder.iterdir():
            if not doc_folder.is_dir():
                continue
            review_file = doc_folder / "review.json"
            if not review_file.exists():
                continue
            try:
                with review_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                status = data.get("status", "New")
                counts["total"] += 1
                if status in counts:
                    counts[status] += 1
                else:
                    counts[status] = counts.get(status, 0) + 1
            except Exception:
                counts["total"] += 1

    return jsonify({"client": client_name, "counts": counts})


def _find_doc_folder(client_name: str, doc_id: str):
    """Find the DOC-XXXXX folder for a client by scanning Batches/date/ folders. Returns Path or None."""
    raw_doc_id = (doc_id or "").strip()
    if len(raw_doc_id) >= 16 and raw_doc_id[10:16] == "__DOC-":
        raw_doc_id = raw_doc_id[12:]

    batches_path = BASE / "Clients" / client_name / "Batches"
    if not batches_path.exists():
        return None
    for date_folder in batches_path.iterdir():
        if not date_folder.is_dir():
            continue
        doc_folder = date_folder / raw_doc_id
        if doc_folder.is_dir() and (doc_folder / "review.json").exists():
            return doc_folder
    return None


@app.route("/docs/<client_name>", methods=["GET"])
def list_docs(client_name: str):
    """Return all documents for a client with review.json data and status counts."""
    batches_path = _client_dir(client_name) / "Batches"
    if not batches_path.exists():
        return jsonify({"error": f"Client not found: {client_name}"}), 404

    docs = []
    counts = {"total": 0, "New": 0, "Verified": 0, "Needs Review": 0, "Failed": 0}
    database_url = os.environ.get("DATABASE_URL", str(BASE / "portal.db"))
    config_cache: dict[str, dict] = {}

    for date_folder in sorted(batches_path.iterdir(), reverse=True):
        if not date_folder.is_dir():
            continue
        batch_date = date_folder.name
        for doc_folder in sorted(date_folder.iterdir()):
            if not doc_folder.is_dir() or not doc_folder.name.startswith("DOC-"):
                continue
            review_file = doc_folder / "review.json"
            if not review_file.exists():
                continue
            try:
                with review_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            status = data.get("status", "New")
            review_meta = data.get("review", {}) or {}
            doc_type = data.get("doc_type", "Unknown")
            config = None
            if doc_type:
                config = config_cache.get(doc_type)
                if config is None:
                    config = document_config.find_document_config(doc_type, database_url)
                    config_cache[doc_type] = config or {}
                if config == {}:
                    config = None
            counts["total"] += 1
            if status in counts:
                counts[status] += 1
            else:
                counts[status] = counts.get(status, 0) + 1
            docs.append({
                "doc_id": data.get("doc_id", doc_folder.name),
                "doc_name": data.get("doc_name"),
                "doc_type": doc_type,
                "status": status,
                "batch_date": batch_date,
                "scanned_at": review_meta.get("scanned_at", ""),
                "reviewed_at": review_meta.get("reviewed_at", ""),
                "exported_at": review_meta.get("exported_at", ""),
                "folder_path": str(doc_folder),
                "fields": data.get("fields", {}),
                "review": data.get("review", {}),
                "page_count": data.get("page_count", 1),
                "required_fields": (config or {}).get("required_fields", []),
                "field_definitions": (config or {}).get("extraction_fields", []),
            })

    return jsonify({"docs": docs, "counts": counts})


@app.route("/review/<client_name>/<doc_id>", methods=["POST"])
def save_review(client_name: str, doc_id: str):
    """Save review data (status, fields, review) to the document's review.json."""
    doc_folder = _find_doc_folder(client_name, doc_id)
    if not doc_folder:
        return jsonify({"success": False, "error": f"Document not found: {client_name} / {doc_id}"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400

    review_path = doc_folder / "review.json"
    try:
        with review_path.open("r", encoding="utf-8") as f:
            current = json.load(f)
    except Exception as e:
        return jsonify({"success": False, "error": f"Cannot read review.json: {e}"}), 500

    if "status" in data:
        current["status"] = data["status"]
    if "fields" in data:
        current["fields"] = data["fields"]
    if "review" in data:
        current["review"] = {**current.get("review", {}), **data["review"]}

    try:
        with review_path.open("w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return jsonify({"success": False, "error": f"Cannot write review.json: {e}"}), 500

    # Auto-sync this document to portal (non-critical; failures are logged only)
    try:
        sync_single_doc(client_name, doc_id)
    except Exception as e:
        app.logger.warning(f"Portal sync failed for {doc_id}: {e}")

    return jsonify({"success": True})


@app.route("/pdf/<client_name>/<doc_id>", methods=["GET"])
def serve_pdf(client_name: str, doc_id: str):
    """Serve the PDF file from the document folder for browser preview."""
    doc_folder = _find_doc_folder(client_name, doc_id)
    if not doc_folder:
        return jsonify({"error": f"Document not found: {client_name} / {doc_id}"}), 404

    pdf_path = None
    for f in doc_folder.iterdir():
        if f.is_file() and f.suffix.lower() == ".pdf":
            pdf_path = f
            break
    if not pdf_path:
        return jsonify({"error": "No PDF found in document folder"}), 404

    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=pdf_path.name
    )


@app.route("/raw-image/<client_name>/<filename>", methods=["GET"])
@app.route("/raw-file/<client_name>/<filename>", methods=["GET"])
def serve_raw_image(client_name: str, filename: str):
    """
    Serve a raw source file from Clients/<client_name>/raw for ScanStation preview.
    This lets the capture UI re-show images or PDFs from a previous session.
    """
    raw_path = _raw_dir(client_name) / filename
    if not raw_path.exists() or not raw_path.is_file():
        return jsonify({"error": f"Raw file not found: {client_name} / {filename}"}), 404

    return send_file(raw_path, as_attachment=False, download_name=raw_path.name)


@app.route("/raw-list/<client_name>", methods=["GET"])
def list_raw_images(client_name: str):
    """
    List raw source files for a client so ScanStation can rebuild
    its session queue after a restart purely from the filesystem.
    """
    raw_dir = _client_dir(client_name) / "raw"
    if not raw_dir.exists() or not raw_dir.is_dir():
        return jsonify({"files": []})

    exts = ALLOWED_RAW_EXTENSIONS
    files = [
        f.name
        for f in sorted(raw_dir.iterdir())
        if f.is_file() and f.suffix.lower() in exts
    ]
    return jsonify({"files": files})


@app.route("/ocr-text/<client_name>/<doc_id>", methods=["GET"])
def ocr_text(client_name: str, doc_id: str):
    """Extract the OCR text layer from the document PDF and return it as plain text."""
    doc_folder = _find_doc_folder(client_name, doc_id)
    if not doc_folder:
        return jsonify({"text": "", "error": f"Document not found: {client_name} / {doc_id}"}), 404

    pdf_path = None
    for f in doc_folder.iterdir():
        if f.is_file() and f.suffix.lower() == ".pdf":
            pdf_path = f
            break
    if not pdf_path:
        return jsonify({"text": "", "error": "No PDF found in document folder"}), 404

    try:
        text = extract_text(str(pdf_path)) or ""
        return jsonify({"text": text, "error": None})
    except Exception as e:
        return jsonify({"text": "", "error": f"Extraction failed: {e}"})


@app.route("/doc-image/<client_name>/<doc_id>", methods=["GET"])
def doc_image(client_name: str, doc_id: str):
    """Serve the raw image from a DOC folder for preview (e.g. rescan panel thumbnail)."""
    doc_folder = _find_doc_folder(client_name, doc_id)
    if not doc_folder:
        return jsonify({"error": "Document not found"}), 404
    for f in doc_folder.iterdir():
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"):
            return send_file(f, as_attachment=False, download_name=f.name)
    return jsonify({"error": "Image not found"}), 404


@app.route("/rescan-replace/<client_name>/<doc_id>", methods=["POST"])
def rescan_replace(client_name: str, doc_id: str):
    """
    Accept a new image to replace the faulty scan for an existing document.
    Saves the new image into the DOC folder, deletes old image/PDF,
    updates review.json to Reprocessing, writes .reprocess trigger for watcher.
    """
    doc_folder = _find_doc_folder(client_name, doc_id)
    if not doc_folder:
        return jsonify({"error": "Document not found"}), 404

    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400
    image_file = request.files["image"]

    review_path = doc_folder / "review.json"
    review_data = {}
    if review_path.exists():
        try:
            with review_path.open("r", encoding="utf-8") as f:
                review_data = json.load(f)
        except Exception as e:
            return jsonify({"error": f"Cannot read review.json: {e}"}), 500

    # Delete old image and PDF files from the DOC folder
    for f in list(doc_folder.iterdir()):
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".pdf"):
            try:
                f.unlink()
            except Exception:
                pass

    ext = (Path(image_file.filename).suffix or ".jpeg").lower()
    if ext not in (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"):
        ext = ".jpeg"
    new_image_name = "rescan" + ext
    new_image_path = doc_folder / new_image_name
    try:
        image_file.save(str(new_image_path))
    except Exception as e:
        return jsonify({"error": f"Failed to save image: {e}"}), 500

    empty_fields = {}
    database_url = os.environ.get("DATABASE_URL", str(BASE / "portal.db"))
    config = document_config.find_document_config((review_data.get("doc_type") or "").strip(), database_url)
    if config:
        for item in config.get("extraction_fields") or []:
            key = item.get("field_key")
            if key:
                empty_fields[key] = ""
    else:
        # Fallback for legacy template-based documents.
        doc_type_raw = (review_data.get("doc_type") or "").strip().lower()
        doc_type_template = DOC_TYPE_TO_TEMPLATE.get(doc_type_raw) or (review_data.get("doc_type_template") or "tenancy_agreement").strip().lower().replace(" ", "_").replace("(", "").replace(")", "")
        if doc_type_template not in ("tenancy_agreement", "gas_safety_certificate", "eicr", "epc", "general_document"):
            doc_type_template = "tenancy_agreement"
        template_path = BASE / "Templates" / f"{doc_type_template}.json"
        if template_path.exists():
            try:
                with template_path.open("r", encoding="utf-8") as f:
                    template = json.load(f)
                for item in template.get("fields", []):
                    if isinstance(item, dict) and "key" in item:
                        empty_fields[item["key"]] = ""
            except Exception:
                pass
    old_property = (review_data.get("fields") or {}).get("property_address", "")
    if old_property:
        empty_fields["property_address"] = old_property

    review_meta = review_data.get("review") or {}
    review_data["status"] = "Reprocessing"
    review_data["fields"] = empty_fields
    review_data["files"] = {"raw_image": new_image_name, "raw_source": new_image_name, "pdf": ""}
    review_data["review"] = {
        "reviewed_by": review_meta.get("reviewed_by", ""),
        "reviewed_at": review_meta.get("reviewed_at", ""),
        "scanned_at": "",
        "notes": review_meta.get("notes", ""),
        "exported_at": review_meta.get("exported_at", ""),
    }
    review_data["rescan_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with review_path.open("w", encoding="utf-8") as f:
            json.dump(review_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return jsonify({"error": f"Cannot write review.json: {e}"}), 500

    trigger_path = doc_folder / ".reprocess"
    try:
        trigger_path.write_text(new_image_name, encoding="utf-8")
    except Exception as e:
        return jsonify({"error": f"Cannot write trigger: {e}"}), 500

    return jsonify({
        "success": True,
        "doc_id": doc_id,
        "message": "New image saved. Waiting for reprocessing.",
    })


@app.route("/reprocess/<client_name>/<doc_id>", methods=["POST"])
def reprocess_doc(client_name: str, doc_id: str):
    """
    Mark a document for rescan. Does NOT copy to raw — document stays in DOC folder
    waiting for replacement via /rescan-replace. Sets status to Sent to Rescan and
    records reason in review.json and rescan_queue.json.
    """
    doc_folder = _find_doc_folder(client_name, doc_id)
    if not doc_folder:
        return jsonify({"success": False, "error": f"Document not found: {client_name} / {doc_id}"}), 404

    review_path = doc_folder / "review.json"
    if not review_path.exists():
        return jsonify({"success": False, "error": "review.json not found"}), 404

    try:
        with review_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return jsonify({"success": False, "error": f"Cannot read review.json: {e}"}), 500

    data_req = request.get_json(silent=True) or {}
    reason = (data_req.get("reason") or "").strip() or "No reason given"

    data["status"] = "Sent to Rescan"
    review_meta = data.get("review") or {}
    review_meta["notes"] = f"Rescan requested: {reason}"
    review_meta["reviewed_by"] = review_meta.get("reviewed_by", "")
    review_meta["reviewed_at"] = review_meta.get("reviewed_at", "")
    data["review"] = review_meta
    data["rescan_requested_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with review_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return jsonify({"success": False, "error": f"Cannot write review.json: {e}"}), 500

    queue_dir = BASE / "Clients" / client_name
    queue_dir.mkdir(parents=True, exist_ok=True)
    queue_path = queue_dir / "rescan_queue.json"
    queue = []
    if queue_path.exists():
        try:
            with queue_path.open("r", encoding="utf-8") as f:
                queue = json.load(f) or []
        except Exception:
            queue = []
    if not any(item.get("doc_id") == doc_id for item in queue):
        queue.append({
            "doc_id": doc_id,
            "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reason": reason,
        })
        try:
            with queue_path.open("w", encoding="utf-8") as f:
                json.dump(queue, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    return jsonify({"success": True, "doc_id": doc_id, "message": "Marked for rescan"})


@app.route("/exports/<client_name>", methods=["GET"])
def list_exports(client_name: str):
    """List previous export deliveries for a client."""
    exports_dir = BASE / "Clients" / client_name / "Exports"
    if not exports_dir.exists():
        return jsonify({"exports": []})

    export_entries = []
    try:
        for d in exports_dir.iterdir():
            if not d.is_dir():
                continue
            if not d.name.startswith("Delivery_"):
                continue
            # Count PDFs inside this delivery folder
            pdf_count = 0
            for f in d.rglob("*.pdf"):
                if f.is_file():
                    pdf_count += 1
            # Date string from folder name (Delivery_YYYY-MM-DD_HHMM)
            date_str = d.name.replace("Delivery_", "", 1)
            export_entries.append({
                "folder_name": d.name,
                "date": date_str,
                "document_count": pdf_count,
            })
        # Newest first by folder name (timestamp embedded)
        export_entries.sort(key=lambda e: e["folder_name"], reverse=True)
    except Exception as e:
        return jsonify({"exports": [], "error": f"Failed to read exports: {e}"}), 500

    return jsonify({"exports": export_entries})


@app.route("/rescan-queue/<client_name>", methods=["GET"])
def get_rescan_queue(client_name: str):
    """Return the list of documents with a pending re-scan request, with doc_name, doc_type, reason, has_image."""
    queue_path = BASE / "Clients" / client_name / "rescan_queue.json"
    if not queue_path.exists():
        return jsonify({"queue": []})
    try:
        with queue_path.open("r", encoding="utf-8") as f:
            raw_queue = json.load(f) or []
    except Exception:
        raw_queue = []
    queue = []
    for item in raw_queue:
        doc_id = item.get("doc_id")
        if not doc_id:
            continue
        doc_folder = _find_doc_folder(client_name, doc_id)
        doc_name = ""
        doc_type = ""
        has_image = False
        if doc_folder:
            review_path = doc_folder / "review.json"
            if review_path.exists():
                try:
                    with review_path.open("r", encoding="utf-8") as f:
                        rev = json.load(f)
                    doc_name = (rev.get("doc_name") or "").strip()
                    doc_type = (rev.get("doc_type") or rev.get("doc_type_template") or "").strip()
                    if not doc_type:
                        doc_type = "Unknown"
                except Exception:
                    pass
            for f in doc_folder.iterdir():
                if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"):
                    has_image = True
                    break
        queue.append({
            "doc_id": doc_id,
            "doc_name": doc_name or doc_id,
            "doc_type": doc_type or "Unknown",
            "reason": item.get("reason") or "No reason given",
            "requested_at": item.get("requested_at") or "",
            "has_image": has_image,
        })
    return jsonify({"queue": queue})


# ──────────────────────────────────────────────
# MERGE / SPLIT
# ──────────────────────────────────────────────

@app.route("/merge/<client_name>", methods=["POST"])
def merge_docs(client_name: str):
    """Merge 2+ DOC records into a single multi-page document."""
    data = request.get_json(silent=True)
    if not data or not isinstance(data.get("doc_ids"), list) or len(data["doc_ids"]) < 2:
        return jsonify({"success": False, "error": "Provide at least 2 doc_ids"}), 400

    doc_ids: list[str] = data["doc_ids"]

    # Validate all DOC folders exist and collect (folder, pdf_path, review_data)
    doc_infos: list[tuple[Path, Path, dict]] = []
    for did in doc_ids:
        folder = _find_doc_folder(client_name, did)
        if not folder:
            return jsonify({"success": False, "error": f"Document not found: {did}"}), 404
        pdf = _find_pdf(folder)
        if not pdf:
            return jsonify({"success": False, "error": f"No PDF in {did}"}), 400
        review_path = folder / "review.json"
        try:
            with review_path.open("r", encoding="utf-8") as f:
                review = json.load(f)
        except Exception as e:
            return jsonify({"success": False, "error": f"Cannot read review.json for {did}: {e}"}), 500
        doc_infos.append((folder, pdf, review))

    base_folder, base_pdf, base_review = doc_infos[0]
    base_doc_id = doc_ids[0]
    consumed = doc_infos[1:]
    consumed_ids = doc_ids[1:]

    try:
        # 1. Merge PDFs
        writer = PdfWriter()
        for _, pdf_path, _ in doc_infos:
            reader = PdfReader(str(pdf_path))
            for page in reader.pages:
                writer.add_page(page)
        merged_pdf_name = f"merged_{base_doc_id}.pdf"
        merged_pdf_path = base_folder / merged_pdf_name
        with open(str(merged_pdf_path), "wb") as out:
            writer.write(out)
        total_pages = len(writer.pages)

        # Remove the old base PDF if it's a different file
        if base_pdf.name != merged_pdf_name and base_pdf.exists():
            base_pdf.unlink()

        # 2. Move raw images from consumed folders into base folder
        IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"}
        all_raw_images = []
        for f in base_folder.iterdir():
            if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                all_raw_images.append(f.name)
        for c_folder, c_pdf, _ in consumed:
            for f in list(c_folder.iterdir()):
                if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                    dest = base_folder / f.name
                    if dest.exists():
                        dest = base_folder / f"{c_folder.name}_{f.name}"
                    shutil.move(str(f), str(dest))
                    all_raw_images.append(dest.name)

        # 3. Update base review.json
        base_review["doc_type"] = "Unknown"
        base_review["doc_type_template"] = ""
        base_review["status"] = "New"
        base_review["files"]["pdf"] = merged_pdf_name
        base_review["files"]["raw_images"] = all_raw_images
        if all_raw_images:
            base_review["files"]["raw_image"] = all_raw_images[0]
        base_review["page_count"] = total_pages
        base_review["fields"] = base_review.get("fields", {})
        base_review.pop("quality_score", None)
        base_review.pop("completeness_score", None)
        base_review.pop("missing_fields", None)
        base_review.pop("needs_attention", None)

        review_path = base_folder / "review.json"
        with review_path.open("w", encoding="utf-8") as f:
            json.dump(base_review, f, indent=2, ensure_ascii=False)

        # 4. Delete consumed DOC folders
        for c_folder, _, _ in consumed:
            shutil.rmtree(str(c_folder), ignore_errors=True)

        # 5. AI prefill on merged doc (best-effort)
        _run_ai_prefill(base_folder)

        # 6. Sync merged doc to portal
        try:
            sync_single_doc(client_name, base_doc_id)
        except Exception as e:
            app.logger.warning(f"Portal sync failed for merged {base_doc_id}: {e}")

        # 7. Remove consumed doc rows from portal
        for cid in consumed_ids:
            try:
                _remove_doc_from_portal(client_name, cid)
            except Exception as e:
                app.logger.warning(f"Portal cleanup failed for {cid}: {e}")

        return jsonify({
            "success": True,
            "merged_doc_id": base_doc_id,
            "page_count": total_pages,
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Merge failed: {e}"}), 500


@app.route("/split/<client_name>/<doc_id>", methods=["POST"])
def split_doc(client_name: str, doc_id: str):
    """Split a multi-page DOC into individual single-page documents."""
    doc_folder = _find_doc_folder(client_name, doc_id)
    if not doc_folder:
        return jsonify({"success": False, "error": f"Document not found: {doc_id}"}), 404

    pdf_path = _find_pdf(doc_folder)
    if not pdf_path:
        return jsonify({"success": False, "error": f"No PDF in {doc_id}"}), 400

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        return jsonify({"success": False, "error": f"Cannot read PDF: {e}"}), 500

    if len(reader.pages) < 2:
        return jsonify({"success": False, "error": "Document has only 1 page — nothing to split"}), 400

    review_path = doc_folder / "review.json"
    try:
        with review_path.open("r", encoding="utf-8") as f:
            parent_review = json.load(f)
    except Exception as e:
        return jsonify({"success": False, "error": f"Cannot read review.json: {e}"}), 500

    batch_folder = doc_folder.parent  # e.g. Batches/2026-03-26

    try:
        new_doc_ids: list[str] = []
        new_folders: list[Path] = []

        for i, page in enumerate(reader.pages):
            new_id = _get_next_doc_id(batch_folder)
            new_folder = batch_folder / new_id
            new_folder.mkdir(parents=True, exist_ok=True)

            # Write single-page PDF
            writer = PdfWriter()
            writer.add_page(page)
            new_pdf_name = f"page_{i + 1}.pdf"
            new_pdf_path = new_folder / new_pdf_name
            with open(str(new_pdf_path), "wb") as out:
                writer.write(out)

            # Write review.json for this page
            scanned_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            child_review = {
                "doc_id": new_id,
                "doc_type": "Unknown",
                "doc_type_template": "",
                "status": "New",
                "quality_score": "",
                "files": {"pdf": new_pdf_name, "raw_image": ""},
                "fields": dict(parent_review.get("fields", {})),
                "review": {
                    "reviewed_by": "",
                    "reviewed_at": "",
                    "exported_at": "",
                    "scanned_at": scanned_at,
                    "notes": f"Split from {doc_id} (page {i + 1})",
                },
                "page_count": 1,
            }
            doc_name = parent_review.get("doc_name")
            if doc_name:
                child_review["doc_name"] = f"{doc_name} (p{i + 1})"

            child_path = new_folder / "review.json"
            with child_path.open("w", encoding="utf-8") as f:
                json.dump(child_review, f, indent=2, ensure_ascii=False)

            new_doc_ids.append(new_id)
            new_folders.append(new_folder)

        # Delete original DOC folder
        shutil.rmtree(str(doc_folder), ignore_errors=True)

        # AI prefill + portal sync for each new doc
        for new_id, new_folder in zip(new_doc_ids, new_folders):
            _run_ai_prefill(new_folder)
            try:
                sync_single_doc(client_name, new_id)
            except Exception as e:
                app.logger.warning(f"Portal sync failed for split {new_id}: {e}")

        # Remove parent doc from portal
        try:
            _remove_doc_from_portal(client_name, doc_id)
        except Exception as e:
            app.logger.warning(f"Portal cleanup failed for parent {doc_id}: {e}")

        return jsonify({
            "success": True,
            "new_doc_ids": new_doc_ids,
            "page_count": len(new_doc_ids),
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Split failed: {e}"}), 500


# ──────────────────────────────────────────────
# STARTUP
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("ScanStation API Server")
    print(f"Running on http://{HOST}:{PORT}")
    print(f"Data root (BASE): {BASE}")
    print("=" * 50)
    print()
    print("Endpoints:")
    print(f"  GET  http://{HOST}:{PORT}/health")
    print(f"  GET  http://{HOST}:{PORT}/clients")
    print(f"  POST http://{HOST}:{PORT}/export")
    print(f"  GET  http://{HOST}:{PORT}/stats/<client>")
    print(f"  GET  http://{HOST}:{PORT}/docs/<client>")
    print(f"  POST http://{HOST}:{PORT}/review/<client>/<doc_id>")
    print(f"  GET  http://{HOST}:{PORT}/pdf/<client>/<doc_id>")
    print(f"  GET  http://{HOST}:{PORT}/doc-image/<client>/<doc_id>")
    print(f"  GET  http://{HOST}:{PORT}/ocr-text/<client>/<doc_id>")
    print(f"  POST http://{HOST}:{PORT}/reprocess/<client>/<doc_id>")
    print(f"  POST http://{HOST}:{PORT}/rescan-replace/<client>/<doc_id>")
    print(f"  GET  http://{HOST}:{PORT}/rescan-queue/<client>")
    print(f"  GET  http://{HOST}:{PORT}/exports/<client>")
    print(f"  POST http://{HOST}:{PORT}/merge/<client>")
    print(f"  POST http://{HOST}:{PORT}/split/<client>/<doc_id>")
    print()
    print("Press Ctrl+C to stop.")
    print()

    app.run(host=HOST, port=PORT, debug=False)
