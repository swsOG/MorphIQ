import time
import json
import shutil
import subprocess
import sys
import os
import re
from pathlib import Path
from datetime import datetime

from portal_new.ai_runtime import load_project_env
from sync_to_portal import sync_single_doc

load_project_env(Path(__file__).parent)

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────

BASE = Path(__file__).resolve().parent
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


def peek_meta_group_id(image_path: Path, raw_folder: Path) -> str | None:
    """Read group_id from .meta.json without deleting the file. Returns None if no group_id."""
    meta_path = raw_folder / (image_path.name + ".meta.json")
    if not meta_path.exists():
        return None
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            meta = json.load(f)
        return meta.get("group_id") or None
    except Exception:
        return None


def collect_group_images(group_id: str, raw_folder: Path) -> list[tuple[Path, dict]]:
    """Find all images in raw_folder belonging to the given group_id, sorted by page_number."""
    members = []
    for meta_file in raw_folder.glob("*.meta.json"):
        try:
            with meta_file.open("r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("group_id") != group_id:
                continue
            image_name = meta_file.name[: -len(".meta.json")]
            image_path = raw_folder / image_name
            if image_path.exists():
                members.append((image_path, meta))
        except Exception:
            continue
    members.sort(key=lambda x: x[1].get("page_number", 0))
    return members


def process_group(group_id: str, members: list[tuple[Path, dict]],
                  raw_folder: Path, batches_folder: Path, client_name: str):
    """Process a completed multi-page document group into a single DOC folder
    with a combined searchable PDF.

    For a group with only one page, delegates to the normal single-file path.
    """
    log(f"GROUP START: {group_id} with {len(members)} pages", client_name)

    # ── Edge case: single page → delegate to normal pipeline ──
    if len(members) == 1:
        image_path = members[0][0]
        log(f"  Single-page group — processing as normal document", client_name)
        process_file(image_path, raw_folder, batches_folder, client_name)
        _cleanup_group_files(group_id, members, raw_folder)
        return

    # ── Wait for every page to be fully written ──
    for image_path, _meta in members:
        wait_until_stable(image_path)

    # ── Extract doc info from first page's meta ──
    first_meta = members[0][1]
    doc_name = (first_meta.get("doc_name") or "").strip() or None
    initial_fields = {}
    prop = (first_meta.get("property_address") or "").strip()
    if prop:
        initial_fields["property_address"] = prop

    if doc_name:
        log(f"  Doc name: {doc_name}", client_name)
    log("  Doc type: Unknown (AI classification pending)", client_name)

    # ── Create DOC folder ──
    today = datetime.now().strftime("%Y-%m-%d")
    batch_folder = batches_folder / today
    doc_id = get_next_doc_id(batch_folder)
    doc_folder = batch_folder / doc_id
    doc_folder.mkdir(parents=True, exist_ok=True)
    log(f"  DocID: {doc_id} -> {doc_folder}", client_name)

    first_image = members[0][0]
    output_pdf = doc_folder / (first_image.stem + ".pdf")
    temp_pngs: list[Path] = []
    temp_tiff = TEMP / f"{client_name}_{group_id}_combined.tiff"

    try:
        # ── 1. Preprocess each page with ImageMagick ──
        for i, (image_path, meta) in enumerate(members):
            page_num = meta.get("page_number", i + 1)
            log(f"  Preprocessing page {page_num}: {image_path.name}", client_name)
            temp_png = TEMP / f"{client_name}_{group_id}_p{page_num}.png"
            preprocess_for_ocr(image_path, temp_png, client_name)
            temp_pngs.append(temp_png)

        # ── 2. Merge preprocessed PNGs into a multi-page TIFF ──
        merge_cmd = [MAGICK] + [str(p) for p in temp_pngs] + ["-density", "300", str(temp_tiff)]
        log("ImageMagick merge: " + " ".join(merge_cmd), client_name)
        proc = subprocess.run(merge_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if proc.stdout:
            log(proc.stdout, client_name)
        if proc.returncode != 0:
            raise RuntimeError(f"ImageMagick merge failed with code {proc.returncode}")

        # ── 3. OCR the multi-page TIFF into a single searchable PDF ──
        ocr_to_pdf(temp_tiff, output_pdf, client_name)

        # ── 4. Move ALL raw images into the DOC folder ──
        archived_names: list[str] = []
        for image_path, _meta in members:
            archived = doc_folder / image_path.name
            shutil.move(str(image_path), str(archived))
            archived_names.append(archived.name)

        # ── 5. Write review.json (first page's meta for doc_name / property) ──
        scanned_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        review = {
            "doc_id": doc_id,
            "doc_type": "Unknown",
            "doc_type_template": "",
            "status": "New",
            "quality_score": "",
            "files": {
                "pdf": output_pdf.name,
                "raw_image": archived_names[0],
                "raw_source": archived_names[0],
                "raw_images": archived_names,
            },
            "fields": {},
            "review": {
                "reviewed_by": "",
                "reviewed_at": "",
                "exported_at": "",
                "scanned_at": scanned_at,
                "notes": "",
            },
            "group_id": group_id,
            "page_count": len(members),
        }
        if doc_name:
            review["doc_name"] = doc_name
        review_path = doc_folder / "review.json"
        with review_path.open("w", encoding="utf-8") as f:
            json.dump(review, f, indent=2, ensure_ascii=False)

        # ── 6. AI prefill ──
        run_ai_prefill(doc_folder, client_name)

        # ── 7. Sync the AI-classified review.json into portal.db ──
        # Runs after prefill so doc_type and fields reflect the real classification.
        # Works even if prefill failed or was skipped (Unknown type, needs_attention).
        try:
            sync_single_doc(client_name, doc_id)
            log(f"Portal sync complete for {doc_id}", client_name)
        except Exception as e:
            log(f"WARN: portal sync failed for {doc_id}: {e}", client_name)

        log(f"GROUP SUCCESS: {group_id} -> {doc_id} ({len(members)} pages)", client_name)
        log(f"  PDF:    {output_pdf}", client_name)
        log(f"  Images: {', '.join(archived_names)}", client_name)
        log(f"  Review: {review_path}", client_name)

    except Exception as e:
        log(f"GROUP ERROR: {group_id}: {e}", client_name)
        for image_path, _meta in members:
            archived = doc_folder / image_path.name
            if not image_path.exists() and archived.exists():
                try:
                    shutil.move(str(archived), str(image_path))
                except Exception:
                    pass
        try:
            if doc_folder.exists() and not any(doc_folder.iterdir()):
                doc_folder.rmdir()
        except Exception:
            pass
        raise
    finally:
        for tp in temp_pngs:
            try:
                if tp.exists():
                    tp.unlink()
            except Exception:
                pass
        try:
            if temp_tiff.exists():
                temp_tiff.unlink()
        except Exception:
            pass

    # ── 8. Clean up meta files and marker on success ──
    _cleanup_group_files(group_id, members, raw_folder)


def _cleanup_group_files(group_id: str, members: list[tuple[Path, dict]],
                         raw_folder: Path):
    """Remove .meta.json sidecars for every group member and the .group_complete marker."""
    for image_path, _meta in members:
        meta_path = raw_folder / (image_path.name + ".meta.json")
        try:
            if meta_path.exists():
                meta_path.unlink()
        except Exception:
            pass
    marker_path = raw_folder / f"{group_id}.group_complete"
    try:
        if marker_path.exists():
            marker_path.unlink()
    except Exception:
        pass


def process_complete_groups(raw_folder: Path, batches_folder: Path, client_name: str):
    """Scan for .group_complete markers and hand each ready group to process_group."""
    for marker in raw_folder.glob("*.group_complete"):
        group_id = marker.stem
        members = collect_group_images(group_id, raw_folder)
        if not members:
            try:
                marker.unlink()
            except Exception:
                pass
            continue
        try:
            process_group(group_id, members, raw_folder, batches_folder, client_name)
        except Exception as e:
            log(f"ERROR (skipping group): {group_id}: {e}", client_name)


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

def write_review_json(
    doc_folder: Path,
    doc_id: str,
    pdf_name: str,
    image_name: str,
    template: dict,
    doc_name: str | None = None,
    initial_fields: dict | None = None,
    raw_source_name: str | None = None,
):
    scanned_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fields = dict(initial_fields or {})
    review = {
        "doc_id": doc_id,
        # Initial doc_type is neutral/unknown; AI prefill will classify it.
        "doc_type": "Unknown",
        # No template is bound at capture time; ReviewStation layout will be
        # driven by whatever fields AI extraction writes later.
        "doc_type_template": "",
        "status": "New",
        "quality_score": "",
        "files": {
            "pdf": pdf_name,
            "raw_image": image_name,
            "raw_source": raw_source_name or image_name or pdf_name,
        },
        # Preserve any metadata captured at scan time before AI prefill augments it.
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
                    review_data["files"] = {
                        "pdf": pdf_filename,
                        "raw_image": image_filename,
                        "raw_source": image_filename,
                    }
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
    doc_name = None
    initial_fields = {}
    if meta:
        doc_name = (meta.get("doc_name") or "").strip() or None
        if doc_name:
            log(f"  Doc name: {doc_name}", client_name)
        prop = (meta.get("property_address") or "").strip()
        if prop:
            initial_fields["property_address"] = prop

    # At capture time we no longer select a template or document type. All
    # documents start as "Unknown" and AI classification assigns the real type.
    log("  Doc type: Unknown (AI classification pending)", client_name)

    today = datetime.now().strftime("%Y-%m-%d")
    batch_folder = batches_folder / today
    doc_id = get_next_doc_id(batch_folder)

    doc_folder = batch_folder / doc_id
    doc_folder.mkdir(parents=True, exist_ok=True)
    log(f"  DocID: {doc_id} -> {doc_folder}", client_name)

    input_suffix = image_path.suffix.lower()
    is_pdf_input = input_suffix == ".pdf"
    output_pdf = doc_folder / (image_path.stem + ".pdf")
    temp_png = TEMP / (f"{client_name}_{image_path.stem}_ocr.png")

    try:
        archived_image_name = ""
        raw_source_name = image_path.name
        if is_pdf_input:
            ocr_to_pdf(image_path, output_pdf, client_name)
            image_path.unlink(missing_ok=True)
        else:
            preprocess_for_ocr(image_path, temp_png, client_name)
            ocr_to_pdf(temp_png, output_pdf, client_name)

            archived_image = doc_folder / image_path.name
            shutil.move(str(image_path), str(archived_image))
            archived_image_name = archived_image.name

        review_path = write_review_json(
            doc_folder,
            doc_id,
            output_pdf.name,
            archived_image_name,
            {},
            doc_name=doc_name,
            initial_fields=initial_fields or None,
            raw_source_name=raw_source_name,
        )

        # Trigger AI pre-fill (best-effort, non-blocking for the main pipeline).
        run_ai_prefill(doc_folder, client_name)

        # Sync the now-complete review.json (with AI-classified doc_type and fields)
        # into portal.db. Works whether prefill succeeded, failed, or was skipped —
        # the document will always appear in the portal with whatever data is available.
        try:
            sync_single_doc(client_name, doc_id)
            log(f"Portal sync complete for {doc_id}", client_name)
        except Exception as e:
            log(f"WARN: portal sync failed for {doc_id}: {e}", client_name)

        log(f"SUCCESS: {image_path.name} -> {doc_id}", client_name)
        log(f"  PDF:    {output_pdf}", client_name)
        if archived_image_name:
            log(f"  Image:  {doc_folder / archived_image_name}", client_name)
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
                if file.suffix.lower() in [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".pdf"]:
                    group_id = peek_meta_group_id(file, raw_folder)
                    if group_id is not None:
                        continue
                    try:
                        process_file(file, raw_folder, batches_folder, client_name)
                    except Exception as e:
                        log(f"ERROR (skipping): {file.name}: {e}", client_name)
            process_complete_groups(raw_folder, batches_folder, client_name)
            check_reprocess_triggers(client_name, client_dir)
        time.sleep(2)

if __name__ == "__main__":
    main()
