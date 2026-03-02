# ReviewStation — Reviewing and verifying documents

ReviewStation is where you **open each document**, check the PDF and the extracted fields, correct them if needed, and set the status (Verified, Needs Review, Failed). You can also request a rescan if the scan quality is poor.

---

## Opening ReviewStation

- From ScanStation footer: click **Open Review Station**, or  
- Open **review_station.html** in your browser.

The server must be running (Start_System_v2.bat) so you can load documents and save changes.

---

## Three views

1. **View 1 — Client picker**  
   Choose the client whose documents you want to review.

2. **View 2 — Dashboard**  
   - **Status cards:** New, Needs Review, Failed, Verified, Sent to rescan, All. Click one to filter the table.  
   - **Date filter:** Restrict by batch date.  
   - **Table:** Doc ID, Doc Type, Timeline (Scan / Review / Export), Status. Click a row to open that document.  
   - **Export section:** Message about how many are verified; **Export Client Package** to create the delivery folder (folders + Excel + Viewer). Export History lists past exports.

3. **View 3 — Document review**  
   - **Left:** Verify key fields (property address, dates, names, etc.). Edit any value.  
   - **Right:** PDF preview of the document.  
   - **Review info:** Reviewed by, Notes.  
   - **Actions:** Previous / Next, **Verified**, **Needs Review**, **Failed**, **Request re-scan**.

---

## Reviewing a document

1. Pick the **client** (View 1), then in the dashboard (View 2) click a **status** or **All** and optionally a **date**.
2. Click a **row** in the table to open that document (View 3).
3. Check the **PDF** on the right and the **fields** on the left. Correct any wrong or missing values.
4. Optionally fill **Reviewed by** and **Notes**.
5. Set the status:
   - **Verified** — Ready for export; data is accepted.
   - **Needs Review** — Needs another look or more info.
   - **Failed** — Not usable as-is.
6. Your choice is saved automatically. Use **Next** / **Previous** or go **Back to list** to continue.

---

## Request re-scan

If the scan is blurry, cropped, wrong document, or too dark/light:

1. Click **Request re-scan**.  
2. In the modal, choose a **reason** (Blurry, Cropped, Wrong document, Too dark/light, or Other and type a reason).  
3. Click **Submit Rescan**.

The document’s status becomes **Sent to Rescan**. It disappears from the main queue and appears in ScanStation’s **Rescan Requests** panel. The operator rescans it there (same DOC-ID, no duplicate). After reprocessing, it appears again as **New** for you to review.

---

## Export

- Only **Verified** documents are included in the export.  
- Click **Export Client Package** to create a new Delivery folder (PDFs by property and doc type, Excel index, Viewer).  
- You can open the delivery folder and/or the Viewer from the prompt after export.

---

## Shortcuts (in document review)

| Key | Action |
|-----|--------|
| **1** | Mark Verified |
| **2** | Mark Needs Review |
| **3** | Mark Failed |
| **←** | Previous document |
| **→** | Next document |

---

## OCR text

Use **Show OCR Text** above the PDF to see the raw text extracted from the PDF. Helpful when checking why a field is wrong or empty.
