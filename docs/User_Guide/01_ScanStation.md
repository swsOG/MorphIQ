# ScanStation — Capturing documents

ScanStation is where you **capture** documents: with a camera or by browsing for image files. Each capture is turned into a searchable PDF and added to the session. Someone else will verify the data in ReviewStation.

---

## Opening ScanStation

- **Start_System_v2.bat** opens it automatically, or  
- Open **scan_station.html** in your browser (Chrome or Edge recommended).

The system must be running (Start_System_v2.bat) so that the pipeline can process new captures.

---

## Main screen

- **Left:** Camera preview, **Client** and **Doc Type** dropdowns, **Property** (optional), and the **Session Queue** — the list of documents you’ve captured in this session (or loaded from the client).
- **Centre:** Empty at first; after a capture you see the image or PDF. Buttons: **Select Folder**, **Browse Files**, **Capture Document** (or **Capture Replacement** when doing a rescan).
- **Right:** Session progress (current/target), Session Summary (counts by doc type and property), and **Rescan Requests** — documents that the reviewer asked to rescan.

---

## Capturing a document

1. **Select the client** (or add a new one from the dropdown).
2. **Select the document type** (e.g. Tenancy Agreement, Gas Safety, EICR, EPC, General).
3. Optionally enter a **Property** (e.g. “12 Oak Street”); it’s used for naming and export folders.
4. **Capture:**
   - **Camera:** Position the document, press **Space** or click **Capture Document**.  
   - **Files:** Click **Browse Files** and choose one or more image files (jpg, png, etc.).
5. In **Careful** mode you’ll see a preview and can enter a **document name** (or accept the suggested one), then **Confirm** or **Retake**.  
   In **Quick** mode the document is saved immediately with an auto-generated name.

After each capture, the pipeline (watcher) turns the image into a searchable PDF and adds it to the client’s batch. New documents appear in the Session Queue and in ReviewStation as **New**.

---

## Rescan requests

When the reviewer clicks **Request re-scan** in ReviewStation, the document appears in the **Rescan Requests** panel on the right. Each row shows a thumbnail, doc name, type, reason, and **Rescan Now**.

- Click **Rescan Now** for that document.  
- The centre shows the **old (faulty) image** so you can see what was wrong.  
- Capture the **replacement** (camera or **Browse Files**).  
- The replacement is sent to the **same** document (same DOC-ID); no duplicate is created.  
- **Escape** cancels rescan mode.

---

## Session and progress

- **Session progress** shows how many documents you’ve captured vs your target.  
- **Session Summary** shows counts by document type and by property.  
- The **left queue** lists documents for the selected client (excluding those “Sent to Rescan”). Click one to preview its PDF or image.

---

## Export and Review Station

- When the reviewer has marked documents as **Verified**, use **Export Verified** in the footer to build the client’s delivery package (folders, Excel, Viewer).  
- **Open Review Station** opens the review app in a new tab so you can switch between scanning and reviewing (or use it on another machine if the server is shared).

---

## Shortcuts (ScanStation)

| Key | Action |
|-----|--------|
| **Space** | Capture (when camera is active) or Capture Replacement (in rescan mode) |
| **B** | Browse Files |
| **R** | Retake (discard current capture in Careful mode) |
| **Tab** | Focus document name (Careful mode) |
| **Enter** | Confirm name (Careful mode) |
| **Esc** | Skip / use suggested name, or cancel rescan mode |
| **C** | Back to camera view |

---

## Pipeline status

The footer shows **Pipeline: Idle** or **Pipeline: Offline**. If it’s offline, the watcher or server may not be running — use **Start_System_v2.bat** again.
