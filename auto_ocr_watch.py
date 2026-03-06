import time
import json
import shutil
import subprocess
import sqlite3
import sys
import os
import re
from pathlib import Path
from datetime import datetime

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    try:
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.lstrip().startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ[key] = val
    except Exception:
        pass

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────

BASE = Path(r"C:\ScanSystem_v2")
CLIENTS_DIR = BASE / "Clients"
TEMP = BASE / "temp"
TEMPLATES = BASE / "Templates"

MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16\magick.exe"
DEFAULT_DOC_TYPE = "tenancy_agreement"

# ──────────────────────────────────────────────
# SETUP
# ──────────────────────────────────────────────

TEMP.mkdir(parents=True, exist_ok=True)
TEMPLATES.mkdir(parents=True, exist_ok=True)
CLIENTS_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# TEMPLATE SYSTEM
# ──────────────────────────────────────────────

def load_template(template_name: str) -> dict:
    template_file = TEMPLATES / f"{template_name}.json"
    if template_file.exists():
        with template_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    log(f"WARN: Template '{template_name}' not found, using fallback", client_name=None)
    return {
        "doc_type": template_name.replace("_", " ").title(),
        "display_name": template_name.replace("_", " ").title(),
        "fields": [
            {"key": "property_address", "label": "Property Address", "type": "text"},
            {"key": "notes", "label": "Notes", "type": "text"}
        ]
    }

def get_doc_type_for_file(image_path: Path, raw_folder: Path) -> str:
    """Use _doctype.txt for template name. (.meta.json is read separately in process_file.)"""
    marker = raw_folder / "_doctype.txt"
    if marker.exists():
        try:
            doc_type = marker.read_text(encoding="utf-8").strip()
            if doc_type:
                return doc_type
        except Exception:
            pass
    return DEFAULT_DOC_TYPE


def read_meta_if_present(image_path: Path, raw_folder: Path) -> dict | None:
    """If image has a .meta.json sidecar, return its content and remove the file. Otherwise return None."""
    meta_path = raw_folder / (image_path.name + ".meta.json")
    if not meta_path.exists():
        return None
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            meta = json.load(f)
        meta_path.unlink()
        return meta
    except Exception:
        return None

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def log(msg: str, client_name: str | None = None):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    if client_name:
        log_dir = CLIENTS_DIR / client_name / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "pipeline.log"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(line)
    print(msg, flush=True)

def wait_until_stable(file_path: Path, seconds_stable: float = 1.0, timeout: float = 60.0):
    start = time.time()
    last_size = -1
    stable_since = None
    while True:
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))
        size = file_path.stat().st_size
        now = time.time()
        if size == last_size:
            if stable_since is None:
                stable_since = now
            if (now - stable_since) >= seconds_stable:
                return
        else:
            stable_since = None
            last_size = size
        if (now - start) > timeout:
            raise TimeoutError(f"File never became stable within {timeout}s: {file_path}")
        time.sleep(0.2)

def get_next_doc_id(batch_folder: Path) -> str:
    existing = []
    if batch_folder.exists():
        for item in batch_folder.iterdir():
            if item.is_dir() and item.name.startswith("DOC-"):
                try:
                    num = int(item.name.split("-")[1])
                    existing.append(num)
                except (IndexError, ValueError):
                    pass
    next_num = max(existing, default=0) + 1
    return f"DOC-{next_num:05d}"

def write_review_json(doc_folder: Path, doc_id: str, pdf_name: str, image_name: str, template: dict,
                     doc_name: str | None = None, initial_fields: dict | None = None):
    fields = {}
    for field_def in template.get("fields", []):
        key = field_def["key"]
        fields[key] = (initial_fields or {}).get(key, "")
    scanned_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    review = {
        "doc_id": doc_id,
        "doc_type": template.get("doc_type", "Unknown"),
        "doc_type_template": template.get("display_name", ""),
        "status": "New",
        "quality_score": "",
        "files": {"pdf": pdf_name, "raw_image": image_name},
        "fields": fields,
        "review": {
            "reviewed_by": "",
            "reviewed_at": "",
            "exported_at": "",
            "scanned_at": scanned_at,
            "notes": ""
        }
    }
    if doc_name:
        review["doc_name"] = doc_name
    review_path = doc_folder / "review.json"
    with review_path.open("w", encoding="utf-8") as f:
        json.dump(review, f, indent=2, ensure_ascii=False)
    return review_path


def run_ai_prefill(doc_folder: Path, client_name: str) -> None:
    """Invoke ai_prefill.py for a completed DOC folder, if present.

    This is best-effort: failures are logged but do not stop the pipeline.
    """
    script_path = BASE / "ai_prefill.py"
    if not script_path.is_file():
        log(f"AI prefill script not found at {script_path}, skipping.", client_name)
        return

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), str(doc_folder)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
        )
        output = (proc.stdout or "").strip()
        if proc.returncode != 0:
            log(f"AI prefill failed for {doc_folder.name} (exit {proc.returncode}): {output}", client_name)
        else:
            if output:
                log(f"AI prefill output for {doc_folder.name}: {output}", client_name)
            else:
                log(f"AI prefill completed for {doc_folder.name}", client_name)
    except Exception as e:
        log(f"AI prefill error for {doc_folder.name}: {e}", client_name)

# ──────────────────────────────────────────────
# PROCESSING
# ──────────────────────────────────────────────

def preprocess_for_ocr(input_jpg: Path, output_png: Path, client_name: str):
    cmd = [
        MAGICK, str(input_jpg), "-strip", "-auto-orient",
        "-colorspace", "Gray", "-density", "300",
        "-trim", "+repage",
        "-bordercolor", "white", "-border", "20",
        "-contrast-stretch", "1%x1%",
        "-adaptive-sharpen", "0x1.0",
        str(output_png),
    ]
    log("ImageMagick: " + " ".join(cmd), client_name)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.stdout:
        log(proc.stdout, client_name)

    if proc.returncode != 0:
        raise RuntimeError(f"ImageMagick failed with code {proc.returncode}")

def ocr_to_pdf(input_image: Path, output_pdf: Path, client_name: str):
    cmd = [
        "ocrmypdf", "--image-dpi", "300", "--force-ocr",
        "--deskew", "--rotate-pages",
        "--tesseract-pagesegmode", "4", "-l", "eng",
        str(input_image), str(output_pdf),
    ]
    log("OCRmyPDF: " + " ".join(cmd), client_name)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.stdout:
        log(proc.stdout, client_name)

    if proc.returncode != 0:
        raise RuntimeError(f"OCRmyPDF failed with code {proc.returncode}")


def check_reprocess_triggers(client_name: str, client_dir: Path) -> None:
    """Check for .reprocess trigger files in DOC folders and reprocess them in place."""
    batches_dir = client_dir / "Batches"
    if not batches_dir.is_dir():
        return
    for date_folder in batches_dir.iterdir():
        if not date_folder.is_dir():
            continue
        for doc_folder_name in date_folder.iterdir():
            doc_path = date_folder / doc_folder_name.name
            if not doc_path.is_dir():
                continue
            trigger_path = doc_path / ".reprocess"
            if not trigger_path.is_file():
                continue
            try:
                image_filename = trigger_path.read_text(encoding="utf-8").strip()
            except Exception:
                try:
                    trigger_path.unlink()
                except Exception:
                    pass
                continue
            image_path = doc_path / image_filename
            if not image_path.is_file():
                try:
                    trigger_path.unlink()
                except Exception:
                    pass
                continue
            log(client_name, f"Reprocessing {doc_folder_name.name}: {image_filename}")
            temp_png = TEMP / f"reprocess_{doc_folder_name.name}.png"
            try:
                preprocess_for_ocr(image_path, temp_png, client_name)
                pdf_filename = Path(image_filename).stem + ".pdf"
                pdf_path = doc_path / pdf_filename
                ocr_to_pdf(temp_png, pdf_path, client_name)
                review_path = doc_path / "review.json"
                if review_path.exists():
                    with review_path.open("r", encoding="utf-8") as f:
                        review_data = json.load(f)
                    review_data["status"] = "New"
                    review_data["files"] = {"pdf": pdf_filename, "raw_image": image_filename}
                    review_data.setdefault("review", {})["scanned_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with review_path.open("w", encoding="utf-8") as f:
                        json.dump(review_data, f, indent=2, ensure_ascii=False)
                if temp_png.exists():
                    temp_png.unlink()
                trigger_path.unlink()
                log(client_name, f"Reprocessed {doc_folder_name.name} successfully -> {pdf_filename}")
                # Remove this doc from rescan_queue.json so ScanStation panel updates
                queue_path = client_dir / "rescan_queue.json"
                if queue_path.exists():
                    try:
                        with queue_path.open("r", encoding="utf-8") as f:
                            queue = json.load(f) or []
                        new_queue = [item for item in queue if item.get("doc_id") != doc_folder_name.name]
                        if len(new_queue) != len(queue):
                            with queue_path.open("w", encoding="utf-8") as f:
                                json.dump(new_queue, f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
            except Exception as e:
                log(client_name, f"ERROR reprocessing {doc_folder_name.name}: {e}")
            finally:
                if temp_png.exists():
                    try:
                        temp_png.unlink()
                    except Exception:
                        pass

def process_file(image_path: Path, raw_folder: Path, batches_folder: Path, client_name: str):
    wait_until_stable(image_path)
    log(f"START: {image_path.name}", client_name)

    meta = read_meta_if_present(image_path, raw_folder)
    if meta:
        doc_type_name = (meta.get("doc_type_template") or "").strip() or get_doc_type_for_file(image_path, raw_folder)
        doc_name = (meta.get("doc_name") or "").strip() or None
        initial_fields = {}
        if doc_name:
            log(f"  Doc name: {doc_name}", client_name)
        prop = (meta.get("property_address") or "").strip()
        if prop:
            initial_fields["property_address"] = prop
    else:
        doc_type_name = get_doc_type_for_file(image_path, raw_folder)
        doc_name = None
        initial_fields = {}

    template = load_template(doc_type_name)
    log(f"  Doc type: {template.get('doc_type', 'Unknown')} (template: {doc_type_name})", client_name)

    today = datetime.now().strftime("%Y-%m-%d")
    batch_folder = batches_folder / today
    doc_id = get_next_doc_id(batch_folder)

    doc_folder = batch_folder / doc_id
    doc_folder.mkdir(parents=True, exist_ok=True)
    log(f"  DocID: {doc_id} -> {doc_folder}", client_name)

    output_pdf = doc_folder / (image_path.stem + ".pdf")
    temp_png = TEMP / (f"{client_name}_{image_path.stem}_ocr.png")

    try:
        preprocess_for_ocr(image_path, temp_png, client_name)
        ocr_to_pdf(temp_png, output_pdf, client_name)

        archived_image = doc_folder / image_path.name
        shutil.move(str(image_path), str(archived_image))

        review_path = write_review_json(
            doc_folder, doc_id, output_pdf.name, archived_image.name, template,
            doc_name=doc_name, initial_fields=initial_fields or None
        )

        # Trigger AI pre-fill (best-effort, non-blocking for the main pipeline).
        run_ai_prefill(doc_folder, client_name)

        # Insert a row into the portal documents table for this newly scanned document.
        db = r"C:\ScanSystem_v2\portal.db"
        conn = None
        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()

            source_doc_id = doc_id
            doc_name_value = doc_name or "Scanned Document"
            pdf_path_value = str(output_pdf)
            raw_image_path_value = str(archived_image)
            scanned_at_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_value = "verified"

            # Look up or create client
            cur.execute("SELECT id FROM clients WHERE name = ?", (client_name,))
            row = cur.fetchone()
            if row:
                client_id = row[0]
            else:
                client_slug = client_name.strip().lower().replace(" ", "-") or "client"
                cur.execute(
                    "INSERT INTO clients (name, slug) VALUES (?, ?)",
                    (client_name, client_slug),
                )
                client_id = cur.lastrowid

            # Look up or create property for this client
            property_address = initial_fields.get("property_address") if initial_fields else None
            if not property_address:
                property_address = "Unassigned property"
            cur.execute(
                "SELECT id FROM properties WHERE client_id = ? AND address = ?",
                (client_id, property_address),
            )
            row = cur.fetchone()
            if row:
                property_id = row[0]
            else:
                cur.execute(
                    "INSERT INTO properties (client_id, address) VALUES (?, ?)",
                    (client_id, property_address),
                )
                property_id = cur.lastrowid

            # Look up or create document type
            doc_type_label = template.get("doc_type", doc_type_name)
            cur.execute(
                "SELECT id FROM document_types WHERE label = ?",
                (doc_type_label,),
            )
            row = cur.fetchone()
            if row:
                document_type_id = row[0]
            else:
                doc_type_key = re.sub(r"[^a-z0-9]+", "-", doc_type_name.lower()).strip("-") or "document"
                cur.execute(
                    "INSERT INTO document_types (key, label) VALUES (?, ?)",
                    (doc_type_key, doc_type_label),
                )
                document_type_id = cur.lastrowid

            cur.execute(
                """
                INSERT INTO documents (
                    client_id,
                    property_id,
                    document_type_id,
                    source_doc_id,
                    doc_name,
                    pdf_path,
                    raw_image_path,
                    status,
                    scanned_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    property_id,
                    document_type_id,
                    source_doc_id,
                    doc_name_value,
                    pdf_path_value,
                    raw_image_path_value,
                    status_value,
                    scanned_at_value,
                ),
            )
            conn.commit()
        except Exception as e:
            log(f"WARN: failed to insert document into DB for {doc_id}: {e}", client_name)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

        log(f"SUCCESS: {image_path.name} -> {doc_id}", client_name)
        try:
            env = os.environ.copy()
            prefill_result = subprocess.run(
                ["python", "ai_prefill.py", str(doc_folder)],
                capture_output=True,
                text=True,
                cwd=r"C:\ScanSystem_v2",
                env=env,
            )
            if prefill_result.returncode == 0:
                log(f"AI PREFILL: success for {doc_id}", client_name)
            else:
                log(f"AI PREFILL WARN: {prefill_result.stderr}", client_name)
        except Exception as e:
            log(f"AI PREFILL ERROR: {e}", client_name)
        log(f"  PDF:    {output_pdf}", client_name)
        log(f"  Image:  {archived_image}", client_name)
        log(f"  Review: {review_path}", client_name)

    except Exception as e:
        log(f"ERROR: {image_path.name}: {e}", client_name)
        if not image_path.exists() and (doc_folder / image_path.name).exists():
            if (doc_folder / image_path.name).exists():
                shutil.move(str(doc_folder / image_path.name), str(image_path))
        try:
            if doc_folder.exists() and not any(doc_folder.iterdir()):
                doc_folder.rmdir()
        except Exception:
            pass
        raise
    finally:
        try:
            if temp_png.exists():
                temp_png.unlink()
        except Exception as e:
            log(f"WARN: temp cleanup failed for {temp_png.name}: {e}", client_name)

# ──────────────────────────────────────────────
# MAIN LOOP
# ──────────────────────────────────────────────

def main():
    available = [f.stem for f in TEMPLATES.glob("*.json")]
    log("=" * 50, client_name=None)
    log("WATCHER STARTED (all clients)", client_name=None)
    log(f"  Clients:   {CLIENTS_DIR}", client_name=None)
    log(f"  Templates: {', '.join(available) if available else 'NONE'}", client_name=None)
    log(f"  Default:   {DEFAULT_DOC_TYPE}", client_name=None)
    log("=" * 50, client_name=None)

    while True:
        for client_dir in sorted(CLIENTS_DIR.iterdir()):
            if not client_dir.is_dir():
                continue
            client_name = client_dir.name
            raw_folder = client_dir / "raw"
            raw_folder.mkdir(parents=True, exist_ok=True)
            batches_folder = client_dir / "Batches"

            for file in raw_folder.glob("*"):
                if file.name.startswith("_"):
                    continue
                if file.suffix.lower() in [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"]:
                    try:
                        process_file(file, raw_folder, batches_folder, client_name)
                    except Exception as e:
                        log(f"ERROR (skipping): {file.name}: {e}", client_name)
            check_reprocess_triggers(client_name, client_dir)
        time.sleep(2)

if __name__ == "__main__":
    main()
