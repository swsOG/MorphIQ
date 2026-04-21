"""
simulate_multipage.py — Simulate a multi-page ScanStation capture without a camera.

Copies 2-3 image files into a client's raw/ folder with the correct
.meta.json and .group_complete marker that ScanStation would create.
The watcher will then detect the group and merge them into one multi-page PDF.

USAGE:
    python simulate_multipage.py <client_name> <image1> <image2> [image3] [--doc-name "Tenancy Agreement"]

EXAMPLES:
    python simulate_multipage.py "Sample Agency Alpha" page1.jpg page2.jpg page3.jpg
    python simulate_multipage.py "Sample Agency Alpha" page1.jpg page2.jpg --doc-name "Tenancy Agreement - 101 Example Street"

The script will:
  1. Copy each image into Clients/<client>/raw/ with a timestamped filename
  2. Create .meta.json for each page (with group_id, page_number, total_pages_so_far)
  3. Write the <group_id>.group_complete marker file
  4. The watcher should then pick up the .group_complete and process the group
"""

import sys
import shutil
import json
import time
from pathlib import Path

def main():
    # --- Parse arguments ---
    args = sys.argv[1:]
    
    if len(args) < 3:
        print("Usage: python simulate_multipage.py <client_name> <image1> <image2> [image3] [--doc-name \"name\"]")
        print("Example: python simulate_multipage.py \"Sample Agency Alpha\" page1.jpg page2.jpg page3.jpg")
        sys.exit(1)
    
    client_name = args[0]
    doc_name = "Multi-page Test Document"
    
    # Separate image paths from --doc-name flag
    image_paths = []
    i = 1
    while i < len(args):
        if args[i] == "--doc-name" and i + 1 < len(args):
            doc_name = args[i + 1]
            i += 2
        else:
            image_paths.append(args[i])
            i += 1
    
    if len(image_paths) < 2:
        print("ERROR: Need at least 2 image files to simulate a multi-page document.")
        sys.exit(1)
    
    # --- Validate paths ---
    BASE = Path(__file__).resolve().parent.parent
    raw_dir = BASE / "Clients" / client_name / "raw"
    
    if not raw_dir.exists():
        print(f"ERROR: Client raw folder not found: {raw_dir}")
        print(f"Available clients:")
        clients_dir = BASE / "Clients"
        if clients_dir.exists():
            for d in clients_dir.iterdir():
                if d.is_dir():
                    print(f"  - {d.name}")
        sys.exit(1)
    
    for img in image_paths:
        p = Path(img)
        if not p.exists():
            # Try relative to BASE
            p = BASE / img
        if not p.exists():
            print(f"ERROR: Image file not found: {img}")
            sys.exit(1)
    
    # --- Generate group_id and timestamps ---
    group_id = f"grp_{int(time.time() * 1000)}"
    total_pages = len(image_paths)
    
    print(f"Simulating {total_pages}-page document capture")
    print(f"  Client:   {client_name}")
    print(f"  Doc name: {doc_name}")
    print(f"  Group ID: {group_id}")
    print(f"  Raw dir:  {raw_dir}")
    print()
    
    # --- Copy images and create meta files ---
    for page_num, img_path in enumerate(image_paths, start=1):
        p = Path(img_path)
        if not p.exists():
            p = BASE / img_path
        
        # Create a timestamped filename like ScanStation would
        timestamp = int(time.time() * 1000) + (page_num * 100)  # slight offset per page
        ext = p.suffix.lower()
        dest_filename = f"scan_{timestamp}{ext}"
        dest_path = raw_dir / dest_filename
        
        # Copy the image
        shutil.copy2(p, dest_path)
        print(f"  Page {page_num}: {p.name} -> {dest_filename}")
        
        # Create .meta.json (same format ScanStation writes)
        meta = {
            "client": client_name,
            "doc_name": doc_name,
            "timestamp": timestamp,
            "group_id": group_id,
            "page_number": page_num,
            "total_pages_so_far": page_num
        }
        
        meta_path = raw_dir / f"{dest_filename}.meta.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
        print(f"         meta -> {meta_path.name}")
        
        # Small delay so timestamps are distinct
        time.sleep(0.15)
    
    # --- Write .group_complete marker ---
    marker_path = raw_dir / f"{group_id}.group_complete"
    with open(marker_path, "w") as f:
        f.write(f"completed:{int(time.time() * 1000)}")
    
    print(f"\n  Marker written: {marker_path.name}")
    print(f"\nDone. The watcher should now detect {group_id}.group_complete and process the group.")
    print(f"Watch pipeline.log for progress.")

if __name__ == "__main__":
    main()
