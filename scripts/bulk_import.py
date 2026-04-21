import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
import argparse
import json
import random
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple

# Reuse core pipeline pieces from the watcher
from auto_ocr_watch import (  # type: ignore
    BASE,
    CLIENTS_DIR,
    preprocess_for_ocr,
    ocr_to_pdf,
    write_review_json,
    run_ai_prefill,
)


@dataclass
class ClientConfig:
    code: str
    name: str
    docs: int
    properties: int


CLIENTS: dict[str, ClientConfig] = {
    "A": ClientConfig("A", "Sample Agency Alpha", 50, 5),
    "B": ClientConfig("B", "Sample Agency Beta", 100, 10),
    "C": ClientConfig("C", "Sample Agency Gamma", 150, 15),
    "D": ClientConfig("D", "Sample Agency Delta", 300, 30),
    "E": ClientConfig("E", "Sample Agency Epsilon", 400, 40),
}


BULK_MARKER_FILENAME = ".bulk_import.json"


def log(message: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}", flush=True)


def find_jpgs(source: Path) -> List[Path]:
    exts = {".jpg", ".jpeg", ".JPG", ".JPEG"}
    files = [p for p in sorted(source.iterdir()) if p.is_file() and p.suffix in exts]
    return files


def parse_doc_type_from_filename(path: Path) -> str:
    """
    Extracts the logical doc type string from filenames like:
      0001_inventory.jpg -> inventory
      0002_gas_safety.jpg -> gas_safety
    Falls back to the stem if pattern not present.
    """
    stem = path.stem
    parts = stem.split("_", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return parts[1]
    return stem


def generate_property_addresses(count: int) -> List[str]:
    towns = [
        "Sampletown",
        "Mockford",
        "Demochester",
        "Testham",
        "Fixture Bay",
        "Placeholder Green",
        "Example Cross",
        "Synthetic Fields",
        "Mockbury",
        "Demo Heath",
    ]
    street_bases = [
        "Gilden Way",
        "Station Road",
        "High Street",
        "London Road",
        "Church Lane",
        "Mill Lane",
        "The Avenue",
        "Maple Close",
        "Oak Drive",
        "Willow Crescent",
        "Riverside Walk",
        "Meadow View",
        "Orchard Close",
        "Park View",
        "Queens Road",
        "Kings Close",
        "Ash Grove",
        "Cedar Court",
        "Elm Drive",
        "Beech Avenue",
    ]
    postcodes = [
        "ZX1",
        "ZX2",
        "ZX3",
        "ZX4",
        "ZX5",
        "ZX6",
        "QX1",
        "QX2",
        "QX3",
        "QX4",
        "QX5",
        "QX6",
    ]

    rng = random.Random(42)  # deterministic for repeatable runs
    addresses: List[str] = []
    for _ in range(count):
        number = rng.randint(1, 250)
        street = rng.choice(street_bases)
        town = rng.choice(towns)
        postcode = f"{rng.choice(postcodes)} {rng.randint(1, 9)}{rng.choice('ABCDEFGHJKLMN')}{rng.randint(1, 9)}"
        addresses.append(f"{number} {street}, {town}, {postcode}")
    return addresses


def allocate_docs_for_client(
    client: ClientConfig, images: List[Path]
) -> List[Tuple[Path, str]]:
    """
    Assigns each image to one of the client's synthetic properties.
    Returns list of (image_path, property_address).
    """
    if not images:
        return []
    props = generate_property_addresses(client.properties)
    assignments: List[Tuple[Path, str]] = []
    for idx, img in enumerate(images):
        prop = props[idx % len(props)]
        assignments.append((img, prop))
    return assignments


def compute_existing_max_doc_num(client_dir: Path) -> int:
    """
    Scan all Batches/ folders for this client and return the highest numeric DOC-XXXXX number.
    """
    batches_root = client_dir / "Batches"
    if not batches_root.is_dir():
        return 0

    max_num = 0
    for batch_date_dir in batches_root.iterdir():
        if not batch_date_dir.is_dir():
            continue
        for doc_dir in batch_date_dir.iterdir():
            if not doc_dir.is_dir():
                continue
            name = doc_dir.name
            if not name.startswith("DOC-"):
                continue
            try:
                num = int(name.split("-")[1])
            except (IndexError, ValueError):
                continue
            if num > max_num:
                max_num = num
    return max_num


def iter_doc_ids(start_from: int) -> Iterable[str]:
    n = start_from
    while True:
        n += 1
        yield f"DOC-{n:05d}"


def ensure_client_folder(client: ClientConfig) -> Path:
    client_dir = CLIENTS_DIR / client.name
    client_dir.mkdir(parents=True, exist_ok=True)
    (client_dir / "Batches").mkdir(parents=True, exist_ok=True)
    (client_dir / "Logs").mkdir(parents=True, exist_ok=True)
    (client_dir / "raw").mkdir(parents=True, exist_ok=True)
    return client_dir


def write_bulk_marker(doc_folder: Path, client: ClientConfig, src_image: Path, property_address: str) -> None:
    marker = {
        "client_code": client.code,
        "client_name": client.name,
        "source_image": str(src_image),
        "property_address": property_address,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    marker_path = doc_folder / BULK_MARKER_FILENAME
    try:
        with marker_path.open("w", encoding="utf-8") as f:
            json.dump(marker, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"WARN: failed to write bulk marker in {doc_folder}: {e}")


def process_single_image(
    index: int,
    total: int,
    client: ClientConfig,
    client_dir: Path,
    doc_id: str,
    src_image: Path,
    property_address: str,
    batch_date: str,
) -> None:
    """
    For one image:
      - Create DOC-XXXXX folder
      - Copy original image
      - Run ImageMagick preprocessing
      - Run OCRmyPDF via ocr_to_pdf
      - Write review.json (status New)
      - Run ai_prefill.py (best effort)
    """
    batches_root = client_dir / "Batches"
    batch_folder = batches_root / batch_date
    batch_folder.mkdir(parents=True, exist_ok=True)

    doc_folder = batch_folder / doc_id
    doc_folder.mkdir(parents=True, exist_ok=True)

    original_name = "original" + src_image.suffix.lower()
    original_path = doc_folder / original_name

    try:
        shutil.copy2(src_image, original_path)
    except Exception as e:
        log(f"[{index}/{total}] {doc_id} | {src_image.name} → COPY ERROR: {e}")
        return

    processed_path = doc_folder / "processed.jpg"
    pdf_name = f"{src_image.stem}.pdf"
    pdf_path = doc_folder / pdf_name

    doc_type_hint = parse_doc_type_from_filename(src_image)

    try:
        preprocess_for_ocr(original_path, processed_path, client.name)
    except Exception as e:
        log(f"[{index}/{total}] {doc_id} | {src_image.name} → ImageMagick ERROR: {e}")
        return

    try:
        ocr_to_pdf(processed_path, pdf_path, client.name)
    except Exception as e:
        log(f"[{index}/{total}] {doc_id} | {src_image.name} → OCR ERROR: {e}")
        return

    # Seed minimal review.json (Unknown type, New status). Property address will normally
    # be populated later by AI prefill reading the PDF content.
    try:
        write_review_json(
            doc_folder,
            doc_id,
            pdf_path.name,
            original_path.name,
            {},
            doc_name=doc_type_hint.replace("_", " ").title(),
            initial_fields=None,
        )
    except Exception as e:
        log(f"[{index}/{total}] {doc_id} | {src_image.name} → review.json ERROR: {e}")
        return

    # Mark as synthetic bulk-imported document so cleanup can safely remove it.
    write_bulk_marker(doc_folder, client, src_image, property_address)

    # Trigger AI prefill (Claude) via existing helper. Best-effort; errors are logged and
    # do not stop the bulk run. Respect a small delay between API calls for rate limiting.
    try:
        run_ai_prefill(doc_folder, client.name)
        time.sleep(0.5)
        log(
            f"[{index}/{total}] {doc_id} | {src_image.name} → OCR ✓ → AI Prefill ✓ "
            f"({client.name} / {property_address})"
        )
    except Exception as e:
        log(
            f"[{index}/{total}] {doc_id} | {src_image.name} → OCR ✓ → AI Prefill ERROR: {e} "
            f"({client.name} / {property_address})"
        )


def run_bulk_import(selected_codes: List[str], source: Path) -> None:
    all_images = find_jpgs(source)
    if not all_images:
        raise SystemExit(f"No JPG images found in {source}")

    # Overall distribution across the selected clients
    total_required = sum(CLIENTS[c].docs for c in selected_codes)
    if len(all_images) < total_required:
        log(
            f"WARNING: Source folder has only {len(all_images)} image(s) "
            f"but {total_required} requested. Will process first {len(all_images)}."
        )
        total_required = len(all_images)

    # Slice images for each client according to its configured document count.
    offset = 0
    assignments_per_client: dict[str, List[Tuple[Path, str]]] = {}
    for code in selected_codes:
        cfg = CLIENTS[code]
        need = min(cfg.docs, max(total_required - offset, 0))
        if need <= 0:
            assignments_per_client[code] = []
            continue
        client_images = all_images[offset : offset + need]
        offset += need
        assignments_per_client[code] = allocate_docs_for_client(cfg, client_images)

    # Execute pipeline
    batch_date = datetime.now().strftime("%Y-%m-%d")
    grand_total = sum(len(v) for v in assignments_per_client.values())
    if grand_total == 0:
        log("Nothing to process after allocation.")
        return

    log("=" * 60)
    log("MorphIQ — Bulk Import")
    log(f"Base:    {BASE}")
    log(f"Source:  {source}")
    log(f"Clients: {', '.join(selected_codes)}")
    log(f"Total docs to process: {grand_total}")
    log("=" * 60)

    processed_count = 0
    for code in selected_codes:
        cfg = CLIENTS[code]
        assignments = assignments_per_client.get(code) or []
        if not assignments:
            continue

        client_dir = ensure_client_folder(cfg)
        start_num = compute_existing_max_doc_num(client_dir)
        doc_id_gen = iter_doc_ids(start_num)

        log(f"Client {cfg.code} — {cfg.name}: {len(assignments)} documents")
        for img, addr in assignments:
            processed_count += 1
            doc_id = next(doc_id_gen)
            process_single_image(
                processed_count,
                grand_total,
                cfg,
                client_dir,
                doc_id,
                img,
                addr,
                batch_date,
            )

    log(f"Bulk import complete. Successfully queued {processed_count} document(s) for review.")


def run_cleanup(selected_codes: List[str]) -> None:
    log("=" * 60)
    log("MorphIQ — Bulk Import Cleanup")
    log(f"Clients: {', '.join(selected_codes)}")
    log("=" * 60)

    total_removed = 0
    for code in selected_codes:
        cfg = CLIENTS[code]
        client_dir = CLIENTS_DIR / cfg.name
        batches_root = client_dir / "Batches"
        if not batches_root.is_dir():
            continue

        removed_for_client = 0
        for batch_date_dir in list(batches_root.iterdir()):
            if not batch_date_dir.is_dir():
                continue
            for doc_dir in list(batch_date_dir.iterdir()):
                if not doc_dir.is_dir() or not doc_dir.name.startswith("DOC-"):
                    continue
                marker_path = doc_dir / BULK_MARKER_FILENAME
                if not marker_path.is_file():
                    continue
                try:
                    with marker_path.open("r", encoding="utf-8") as f:
                        meta = json.load(f)
                    if meta.get("client_code") != code:
                        continue
                except Exception:
                    # If marker cannot be read, be conservative and skip.
                    continue

                try:
                    shutil.rmtree(doc_dir)
                    removed_for_client += 1
                except Exception as e:
                    log(f"WARN: failed to remove bulk DOC folder {doc_dir}: {e}")

            # Remove empty batch folders
            try:
                if not any(batch_date_dir.iterdir()):
                    batch_date_dir.rmdir()
            except Exception:
                pass

        if removed_for_client:
            log(f"Client {cfg.code} — {cfg.name}: removed {removed_for_client} DOC folder(s)")
        total_removed += removed_for_client

    log(f"Cleanup complete. Removed {total_removed} bulk-imported DOC folder(s).")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bulk-import 1,000 JPG document images into synthetic DOC-XXXXX "
            "folders for stress-testing the MorphIQ pipeline."
        )
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Path to folder containing input JPGs (e.g. 0001_inventory.jpg).",
    )
    parser.add_argument(
        "--client",
        type=str,
        default="all",
        help="Which client batch to process: A|B|C|D|E|all (default: all).",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove previously bulk-imported DOC folders (per client selection).",
    )
    return parser.parse_args(argv)


def resolve_client_codes(raw: str) -> List[str]:
    raw = (raw or "").strip().lower()
    if raw in ("all", ""):
        return list(CLIENTS.keys())
    codes = [c.strip().upper() for c in raw.split(",") if c.strip()]
    for c in codes:
        if c not in CLIENTS:
            raise SystemExit(f"Invalid client code '{c}'. Expected one of A,B,C,D,E,all.")
    # Preserve user order but deduplicate
    seen = set()
    ordered: List[str] = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def main(argv: List[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    selected_codes = resolve_client_codes(args.client)

    if args.cleanup:
        run_cleanup(selected_codes)
        return

    if not args.source:
        raise SystemExit("--source PATH is required when not running with --cleanup")

    source = Path(args.source)
    if not source.is_dir():
        raise SystemExit(f"--source path is not a directory: {source}")

    run_bulk_import(selected_codes, source)


if __name__ == "__main__":
    main()
