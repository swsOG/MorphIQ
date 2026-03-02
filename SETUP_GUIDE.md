# ScanStation Setup Guide
## Install this system on a new Windows PC

Follow every step in order. Do not skip steps.

---

## STEP 1 — Install Python

1. Open https://www.python.org/downloads/
2. Click "Download Python", run the installer
3. **IMPORTANT:** Tick "Add Python to PATH"
4. Click "Install Now" and finish

**Verify:** Open Command Prompt, run `python --version` (e.g. Python 3.x.x).

---

## STEP 2 — Install Tesseract OCR

1. Open https://github.com/UB-Mannheim/tesseract/wiki
2. Download the Windows installer (.exe), run it
3. Use default location `C:\Program Files\Tesseract-OCR\`; ensure English is selected
4. Add to PATH: Start → "Environment Variables" → System variables → Path → New → `C:\Program Files\Tesseract-OCR\`

**Verify:** New Command Prompt, run `tesseract --version`.

---

## STEP 3 — Install ImageMagick

1. Open https://imagemagick.org/script/download.php#windows
2. Download "Win64 dynamic at 16 bits-per-pixel", run installer
3. Tick "Add application directory to your system path"
4. Use default location

**Verify:** New Command Prompt, run `magick --version`.

---

## STEP 4 — Install Python packages

In Command Prompt, run each command:

```
pip install ocrmypdf
pip install openpyxl
pip install flask
pip install flask-cors
```

Wait for each to complete before the next.

---

## STEP 5 — Install Camo (phone as webcam)

1. On phone: install Camo app (App Store / Google Play)
2. On PC: https://reincubate.com/camo/ — download and install Windows app
3. Connect phone via USB; open Camo on both; camera appears as webcam

---

## STEP 6 — Set up the ScanSystem folder

1. Copy the ScanSystem_v2 folder to `C:\ScanSystem_v2\`

Your folder should look like this:

```
C:\ScanSystem_v2\
├── auto_ocr_watch.py
├── server.py
├── export_client.py
├── scan_station.html
├── review_station.html
├── Start_System_v2.bat
├── Stop_System.bat
├── Stop_Watcher.bat
├── setup_check.bat
├── SETUP_GUIDE.md
├── PROJECT_BRAIN.md
├── Clients\
└── Templates\
    ├── tenancy_agreement.json
    ├── gas_safety_certificate.json
    ├── eicr.json
    ├── epc.json
    └── general_document.json
```

The `Clients` folder will get one subfolder per client. Each client folder gets `raw\`, `Batches\`, `Exports\`, and `Logs\` created automatically when you use the system.

---

## STEP 7 — Test the system

1. Double-click **Start_System_v2.bat** in `C:\ScanSystem_v2\`
   - Starts the **document watcher** (minimised)
   - Starts the **API server** on http://127.0.0.1:8765 (minimised)
   - Opens **ScanStation** in your browser

2. In ScanStation:
   - Click **"Select Folder"** and choose `C:\ScanSystem_v2`
   - Select your camera from the header dropdown
   - Choose **Client** (or "+ Add New Client" and enter a name)
   - Choose **Doc Type** (e.g. Tenancy Agreement)
   - Capture documents (Space or **Capture Document**), or use **Browse Files**
   - In Careful mode you can enter a document name and confirm; in Quick mode captures auto-advance

3. The watcher processes images from the client's `raw` folder into DOC-XXXXX folders. Check `C:\ScanSystem_v2\Clients\<client>\Logs\pipeline.log` if needed.

4. Open **ReviewStation**: click **"Open Review Station"** in the footer (or open `C:\ScanSystem_v2\review_station.html`). Select your client, review documents, set status to Verified / Needs Review / Failed.

5. When you have at least one **Verified** document, on the client dashboard click **"Export Client Package"**. The API server runs the export and shows the delivery folder path.  
   Or from Command Prompt: `python C:\ScanSystem_v2\export_client.py ClientName`

6. To stop: run **Stop_System.bat** in `C:\ScanSystem_v2\` (stops watcher and API server).

---

## Troubleshooting

**"python is not recognized"**  
→ Reinstall Python and tick "Add to PATH".

**"tesseract is not recognized"**  
→ Add `C:\Program Files\Tesseract-OCR\` to system PATH (Step 2).

**Camera doesn't appear**  
→ Camo running on phone and PC; try another USB cable; use Chrome or Edge.

**Watcher doesn't process files**  
→ Check the minimised "ScanStation Watcher" window. Ensure you chose the ScanSystem folder in ScanStation (Select Folder → `C:\ScanSystem_v2`).

**ReviewStation: "Server unreachable" or blank list**  
→ API server must be running. Use **Start_System_v2.bat** (it starts the server), or run `python C:\ScanSystem_v2\server.py` in a separate Command Prompt.

**Export button does nothing or errors**  
→ API server running; at least one document must be **Verified** for that client.

**"No cameras found"**  
→ Allow camera permission in the browser; if blocked, use the camera icon in the address bar to allow.

**Full system check**  
→ Double-click **setup_check.bat** in `C:\ScanSystem_v2\`. It checks Python, Tesseract, ImageMagick, ocrmypdf, openpyxl, flask, flask-cors, and the folder.

---

## Daily Workflow

1. Double-click **Start_System_v2.bat** in `C:\ScanSystem_v2\`
   - Starts the document watcher
   - Starts the **API server** (needed for ReviewStation and Export)
   - Opens ScanStation in the browser

2. In **ScanStation**: select or add client, choose doc type, capture documents (camera or Browse Files). Watcher turns each image into a DOC-XXXXX folder.

3. In **ReviewStation**: select client, review documents, set Verified / Needs Review / Failed.

4. When ready to deliver: in ReviewStation dashboard click **"Export Client Package"**. Package is created under `C:\ScanSystem_v2\Clients\<ClientName>\Exports\Delivery_YYYY-MM-DD_HHMM\`.

5. When finished: run **Stop_System.bat** to stop the watcher and the API server.
