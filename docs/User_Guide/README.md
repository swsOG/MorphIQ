# ScanStation System — User Guide

This folder explains how to use the document scanning and archiving system. If you're new, start here.

---

## What is this system?

The system turns **paper documents** (tenancy agreements, gas certificates, EICRs, EPCs, etc.) into **searchable PDFs** with **verified key information** (addresses, dates, names). It is built for letting agencies and landlords: you capture documents, someone reviews and verifies the data, then you export a tidy package (folders + spreadsheet + searchable archive) for the client.

There are **three main parts**:

| Part | What it does | Who uses it |
|------|----------------|-------------|
| **ScanStation** | Capture documents (camera or file), see session queue and rescan requests | Person scanning (operator) |
| **ReviewStation** | Open each document, check/correct the extracted fields, mark as Verified / Needs Review / Failed, request rescans | Person verifying (reviewer) |
| **Viewer** | Browse and search the final archive (after export); for you or the client | You or the client |

**Typical flow:**  
Scan (ScanStation) → Review & verify (ReviewStation) → Export → Open delivery folder and/or Viewer to check or hand over.

---

## Getting started

1. **Start the system**  
   Double‑click **Start_System_v2.bat** (in the main ScanSystem_v2 folder).  
   This starts the pipeline and server and opens ScanStation in your browser.

2. **First time?**  
   Run **setup_check.bat** once to confirm everything (Python, Tesseract, ImageMagick, etc.) is installed. See **SETUP_GUIDE.md** in the main folder for installing on a new PC.

3. **Open the three parts**  
   - **ScanStation:** Opened by Start_System_v2.bat, or open **scan_station.html** in your browser.  
   - **ReviewStation:** From ScanStation footer click **Open Review Station**, or open **review_station.html**.  
   - **Viewer:** After you export a client, use the link that appears, or open **viewer.html** from inside the client’s Delivery folder.

---

## Quick links to each guide

- **[ScanStation](01_ScanStation.md)** — Capturing documents (camera, browse), session queue, rescan requests, export.
- **[ReviewStation](02_ReviewStation.md)** — Dashboard, reviewing documents, verifying fields, statuses, requesting rescans.
- **[Viewer](03_Viewer.md)** — Browsing and searching the exported archive (properties, document list, PDF + details).

---

## Where are my files?

- **While you work:** Documents live under **Clients\\*ClientName*\\Batches\\*date*\\DOC-XXXXX** (each DOC-XXXXX is one document: PDF, image, and review data).
- **After export:** Each export creates **Clients\\*ClientName*\\Exports\\Delivery_*date*_*time*** with folders by property and document type, an Excel index, and the Viewer (viewer.html + data). You can copy that whole Delivery folder to a USB or send it to the client.

---

## Need help?

- **Technical / setup:** See **SETUP_GUIDE.md** and **PROJECT_BRAIN.md** in the main ScanSystem_v2 folder.  
- **Stopping the system:** Run **Stop_System.bat** to stop the watcher and server.
