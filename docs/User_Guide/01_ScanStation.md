# ScanStation - camera-first intake

ScanStation is the intake screen for getting documents into the pipeline quickly and clearly.

Its job is simple:
- capture a document from the camera rig
- import a document when the camera is unavailable or when testing
- handle rescan requests
- send documents onward for review in ReviewStation

ScanStation is not the place for export or general workflow management.

---

## Opening ScanStation

- Run `Start_System_v2.bat`, or
- open `scan_station.html` in Chrome or Edge

The backend pipeline must be running so captured or imported documents can be processed.

---

## Main screen

- Top bar: choose the `Camera`, `Client`, and optional `Property`
- Left side: live camera preview and the `Session Queue`
- Center: the active capture or preview area
- Action bar: `Capture Document` or `Import Document`
- Right side: compact `Intake Summary` plus any `Rescan Requests`

The screen is now camera-first. If the rig is connected, capture is the primary path. If no camera is available, the screen clearly falls back to import mode.

---

## Normal workflow

1. Select the client.
2. Optionally enter the property address.
3. Place the page under the camera.
4. Press `Space` or click `Capture Document`.
5. The document is sent into the pipeline and appears in the session queue.

If the camera is unavailable, use `Import Document` instead. Imported JPGs and PDFs go through the same backend intake path.

---

## Review Before Save

Turn on `Review Before Save` if you want a confirmation step before the file is committed.

When it is on:
- you see a preview first
- you can adjust the suggested document name
- you can confirm or retake before saving

When it is off:
- capture is faster
- the document is saved immediately

---

## Import fallback

`Import Document` is the fallback path for:
- testing with sample files
- temporary no-camera operation
- exception handling

This is secondary to the normal camera workflow, but it uses the same pipeline and should reach ReviewStation in the same way.

---

## Multi-page documents

Use `Add Page` only when you are building a multi-page document.

While multi-page capture is active:
- `Add Page` adds another page to the current document
- `Finish Document` closes the group and sends it onward

These controls only appear when they are relevant.

---

## Rescans

If ReviewStation requests a rescan, it appears on the right under `Rescan Requests`.

To complete a rescan:
1. click `Rescan Now`
2. preview the existing document
3. capture a replacement or import a replacement file
4. the replacement is sent back through the same document slot

Press `Esc` to cancel rescan mode.

---

## Utilities

`Open Review Station` and `Open Portal` are secondary utilities. They are available from ScanStation, but they are not part of the main intake flow.

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Space` | Capture the current document when the camera is available |
| `B` | Import Document |
| `R` | Retake while reviewing before save |
| `Tab` | Focus the name field during review before save |
| `Enter` | Confirm the reviewed document |
| `Esc` | Skip naming or cancel rescan mode |
| `C` | Return to the camera view when previewing |
| `P` | Add Page during multi-page capture |
| `F` | Finish Document during multi-page capture |

---

## What changed

The current ScanStation no longer uses:
- a document type dropdown
- folder selection
- top-level Quick/Careful buttons
- export controls

The flow is now:
- camera-first intake
- import fallback
- review later in ReviewStation
