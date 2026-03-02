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
import threading
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pdfminer.high_level import extract_text

# Import the export function from the existing export script
from export_client import run_export

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────

BASE = Path(r"C:\ScanSystem_v2")
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
    clients_dir = BASE / "Clients"
    if not clients_dir.exists():
        return jsonify({"clients": []})

    clients = [
        d.name for d in sorted(clients_dir.iterdir())
        if d.is_dir()
    ]
    return jsonify({"clients": clients})


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
        if result.get("success") and result.get("delivery_folder"):
            export_folder_name = Path(result["delivery_folder"]).name
            result["viewer_url"] = f"http://{HOST}:{PORT}/delivery/{quote(client_name)}/{quote(export_folder_name)}/viewer.html"
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
    batches_path = BASE / "Clients" / client_name / "Batches"
    if not batches_path.exists():
        return None
    for date_folder in batches_path.iterdir():
        if not date_folder.is_dir():
            continue
        doc_folder = date_folder / doc_id
        if doc_folder.is_dir() and (doc_folder / "review.json").exists():
            return doc_folder
    return None


@app.route("/docs/<client_name>", methods=["GET"])
def list_docs(client_name: str):
    """Return all documents for a client with review.json data and status counts."""
    batches_path = BASE / "Clients" / client_name / "Batches"
    if not batches_path.exists():
        return jsonify({"error": f"Client not found: {client_name}"}), 404

    docs = []
    counts = {"total": 0, "New": 0, "Verified": 0, "Needs Review": 0, "Failed": 0}

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
            counts["total"] += 1
            if status in counts:
                counts[status] += 1
            else:
                counts[status] = counts.get(status, 0) + 1
            docs.append({
                "doc_id": data.get("doc_id", doc_folder.name),
                "doc_name": data.get("doc_name"),
                "doc_type": data.get("doc_type", "Unknown"),
                "status": status,
                "batch_date": batch_date,
                 # Detailed timeline fields (may be empty for older docs)
                "scanned_at": review_meta.get("scanned_at", ""),
                "reviewed_at": review_meta.get("reviewed_at", ""),
                "exported_at": review_meta.get("exported_at", ""),
                "folder_path": str(doc_folder),
                "fields": data.get("fields", {}),
                "review": data.get("review", {})
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
def serve_raw_image(client_name: str, filename: str):
    """
    Serve a raw image file from Clients/<client_name>/raw for ScanStation preview.
    This lets the capture UI re-show images from a previous session.
    """
    raw_path = BASE / "Clients" / client_name / "raw" / filename
    if not raw_path.exists() or not raw_path.is_file():
        return jsonify({"error": f"Raw image not found: {client_name} / {filename}"}), 404

    return send_file(raw_path, as_attachment=False, download_name=raw_path.name)


@app.route("/raw-list/<client_name>", methods=["GET"])
def list_raw_images(client_name: str):
    """
    List raw image files for a client so ScanStation can rebuild
    its session queue after a restart purely from the filesystem.
    """
    raw_dir = BASE / "Clients" / client_name / "raw"
    if not raw_dir.exists() or not raw_dir.is_dir():
        return jsonify({"files": []})

    exts = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
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

    # Build empty fields from template (fields is array of { key, label, type })
    doc_type_raw = (review_data.get("doc_type") or "").strip().lower()
    doc_type_template = DOC_TYPE_TO_TEMPLATE.get(doc_type_raw) or (review_data.get("doc_type_template") or "tenancy_agreement").strip().lower().replace(" ", "_").replace("(", "").replace(")", "")
    if doc_type_template not in ("tenancy_agreement", "gas_safety_certificate", "eicr", "epc", "general_document"):
        doc_type_template = "tenancy_agreement"
    template_path = BASE / "Templates" / f"{doc_type_template}.json"
    empty_fields = {}
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
    review_data["files"] = {"raw_image": new_image_name, "pdf": ""}
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
# STARTUP
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("ScanStation API Server")
    print(f"Running on http://{HOST}:{PORT}")
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
    print()
    print("Press Ctrl+C to stop.")
    print()

    app.run(host=HOST, port=PORT, debug=False)
