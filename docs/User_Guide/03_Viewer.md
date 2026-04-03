# Viewer — Browsing and searching the archive

The Viewer is the **document archive** for a client. You use it after an export to browse and search all verified documents in that delivery. It can be opened from the export link (over the server) or directly from the Delivery folder (e.g. on a USB for the client).

---

## When do you use the Viewer?

- **After export:** To check that the delivery looks correct (folders, document list, search).  
- **Handover:** Give the client the Delivery folder; they open **viewer.html** to browse and search their archive.  
- **On a USB:** The Delivery folder is self-contained; opening viewer.html from the USB works. For the best experience (including search highlighting on the PDF), open it via the server link once the folder is on a machine that can reach the server.

---

## Opening the Viewer

- **After export:** When you click Export in ReviewStation, you can open the **viewer link** (e.g. `http://127.0.0.1:8765/delivery/ClientName/Delivery_.../viewer.html`) in a new tab.  
- **From the Delivery folder:** Open **viewer.html** from inside  
  `Clients\<ClientName>\Exports\Delivery_<date>_<time>\`  
  (e.g. double-click viewer.html, or drag it into the browser).

---

## Main screen

- **Left:** List of **properties** (or “Unsorted”). Click a property to see its document categories (e.g. Tenancy Agreements, Gas Safety).  
- **Centre:** List of **documents** in the selected category (name, type). Click one to open it in the preview panel.  
- **Right:** **Preview panel** with two tabs:  
  - **Document** — PDF of the selected document.  
  - **Details** — Extracted fields and full text.

---

## Search

- Use the **search box** (e.g. type an address, name, or date).  
- The list filters to matching documents; the **Details** tab shows the match in context with highlights.  
- If you opened the Viewer from the **server URL** (after export), the **Document** tab will also highlight the search term on the PDF.  
- If you opened from a **file** (e.g. USB), a short message may explain that opening from the server improves PDF search highlighting.

---

## Browsing

1. Click a **property** in the left column.  
2. Click a **category** (e.g. Tenancy Agreements) to see its documents.  
3. Click a **document** to open its PDF and details in the preview panel.  
4. Switch between **Document** and **Details** tabs as needed.

---

## What’s in the Delivery folder?

- **viewer.html** — The archive viewer (this app).  
- **archive_data.json** — Data that powers the viewer (embedded in viewer.html when opened from the folder).  
- **Excel file** — Index of all documents with fields and locations.  
- **Property folders** — Each property (or “Unsorted”) has subfolders by document type (e.g. Tenancy Agreements), with PDFs inside.

The client can use the Viewer to search and browse, and use the Excel file for lists and reporting.
