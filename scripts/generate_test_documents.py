"""
MorphIQ Test Document Generator -- JPEG Edition
Generates A4 JPEG images (2480x3508px @ 300dpi) that look like real UK letting
agency documents with clearly laid-out field labels and values for Tesseract OCR.

Output: Clients/Harlow & Essex Lettings/raw/
Each JPEG has a matching .meta.json sidecar.

Usage:
    python generate_test_documents.py
"""

import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow is not installed. Run: pip install Pillow")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE = Path(__file__).resolve().parent.parent
CLIENT_NAME = "Harlow & Essex Lettings"
RAW_DIR = BASE / "Clients" / CLIENT_NAME / "raw"

# A4 at 300 dpi
W, H = 2480, 3508
MARGIN = 160
TITLE_SIZE  = 88
HEADER_SIZE = 58
LABEL_SIZE  = 52
VALUE_SIZE  = 52
LINE_LEAD   = 80   # pixels between field rows


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def _first_existing(paths):
    for p in paths:
        if Path(p).exists():
            return p
    return None


def load_font(size, bold=False):
    if bold:
        ttf = _first_existing([
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
            r"C:\Windows\Fonts\verdanab.ttf",
            r"C:\Windows\Fonts\trebucbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ])
    else:
        ttf = _first_existing([
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
            r"C:\Windows\Fonts\verdana.ttf",
            r"C:\Windows\Fonts\trebuc.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ])
    if ttf:
        try:
            return ImageFont.truetype(ttf, size)
        except Exception:
            pass
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def text_width(draw, text, font):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]
    except AttributeError:
        w, _ = draw.textsize(text, font=font)
        return w


def wrap_text(draw, text, font, max_px):
    """Return list of lines that each fit within max_px."""
    words = text.split()
    if not words:
        return [""]
    lines, current = [], words[0]
    for word in words[1:]:
        candidate = current + " " + word
        if text_width(draw, candidate, font) <= max_px:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Document renderer
# ---------------------------------------------------------------------------

def render_doc(title, fields, output_path):
    """
    Draw one A4 JPEG document.

    fields: list of (label, value) where:
      - (None, None)          -> blank spacer line
      - ("## Section", None)  -> bold section header + rule
      - ("Label", "value")    -> normal label:value row
    """
    img  = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    font_title  = load_font(TITLE_SIZE,  bold=True)
    font_header = load_font(HEADER_SIZE, bold=True)
    font_label  = load_font(LABEL_SIZE,  bold=True)
    font_value  = load_font(VALUE_SIZE,  bold=False)

    text_area = W - 2 * MARGIN   # usable width

    y = MARGIN

    # -- Title ---------------------------------------------------------------
    for line in wrap_text(draw, title, font_title, text_area):
        draw.text((MARGIN, y), line, fill="black", font=font_title)
        y += TITLE_SIZE + 16

    y += 14
    draw.line([(MARGIN, y), (W - MARGIN, y)], fill="#111111", width=6)
    y += 36

    # -- Fields --------------------------------------------------------------
    for label, value in fields:

        # Blank spacer
        if label is None:
            y += LINE_LEAD // 2
            continue

        # Section header  ("## Heading")
        if label.startswith("##"):
            y += 20
            heading = label[2:].strip()
            draw.text((MARGIN, y), heading, fill="#111111", font=font_header)
            y += HEADER_SIZE + 10
            draw.line([(MARGIN, y), (W - MARGIN, y)], fill="#cccccc", width=3)
            y += 22
            continue

        # Normal field: bold label on one line, value indented below
        label_str = f"{label}:"
        draw.text((MARGIN, y), label_str, fill="#111111", font=font_label)
        y += LABEL_SIZE + 8

        value_lines = wrap_text(draw, str(value) if value else "", font_value, text_area - 40)
        for vl in value_lines:
            draw.text((MARGIN + 40, y), vl, fill="#222222", font=font_value)
            y += VALUE_SIZE + 6
        y += 14   # gap after value

        if y > H - MARGIN - 80:
            break   # safety: stop before running off the page

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "JPEG", quality=95)
    return output_path


# ---------------------------------------------------------------------------
# Meta-JSON writer
# ---------------------------------------------------------------------------

def write_meta(jpg_path, address, doc_name, doc_type):
    meta = {
        "client":           CLIENT_NAME,
        "property_address": address,
        "doc_name":         doc_name,
        "doc_type":         doc_type,
    }
    meta_path = jpg_path.parent / (jpg_path.name + ".meta.json")
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta_path


# ---------------------------------------------------------------------------
# Document manifest  (27 documents across 6 properties)
# ---------------------------------------------------------------------------

DOCS = [

    # =========================================================================
    # PROPERTY 1 -- 4 Birchwood Close, Harlow  (all fully valid)
    # =========================================================================
    dict(
        filename = "prop1_gas_safety.jpg",
        title    = "GAS SAFETY CERTIFICATE (CP12)",
        doc_type = "gas_safety",
        address  = "4 Birchwood Close, Harlow, CM17 0PQ",
        doc_name = "Gas Safety Certificate - 4 Birchwood Close",
        fields   = [
            ("Property Address",      "4 Birchwood Close, Harlow, CM17 0PQ"),
            ("Engineer Name",         "Paul Hendry"),
            ("Gas Safe Registration", "612934"),
            ("Inspection Date",       "10 March 2026"),
            ("Expiry Date",           "10 March 2027"),
            ("Result",                "PASS"),
            ("Appliances Inspected",  "Boiler, Gas Hob, Gas Fire"),
            ("Warnings",              "None"),
            ("Landlord",              "H. Patel"),
        ],
    ),
    dict(
        filename = "prop1_eicr.jpg",
        title    = "ELECTRICAL INSTALLATION CONDITION REPORT (EICR)",
        doc_type = "eicr",
        address  = "4 Birchwood Close, Harlow, CM17 0PQ",
        doc_name = "EICR - 4 Birchwood Close",
        fields   = [
            ("Property Address",    "4 Birchwood Close, Harlow, CM17 0PQ"),
            ("Electrician",         "Bright Spark Ltd"),
            ("NICEIC Registration", "7731"),
            ("Inspection Date",     "05 January 2024"),
            ("Next Inspection Due", "05 January 2029"),
            ("Result",              "SATISFACTORY"),
            ("Observations",        "C3 recommendation noted, no immediate action required"),
            ("Landlord",            "H. Patel"),
        ],
    ),
    dict(
        filename = "prop1_epc.jpg",
        title    = "ENERGY PERFORMANCE CERTIFICATE (EPC)",
        doc_type = "epc",
        address  = "4 Birchwood Close, Harlow, CM17 0PQ",
        doc_name = "EPC - 4 Birchwood Close",
        fields   = [
            ("Property Address",         "4 Birchwood Close, Harlow, CM17 0PQ"),
            ("Current Energy Rating",    "B"),
            ("Energy Score",             "85"),
            ("Assessor",                 "EcoAssess UK"),
            ("Assessment Date",          "20 June 2022"),
            ("Valid Until",              "20 June 2032"),
            ("Primary Heating",          "Gas Central Heating"),
            ("Recommended Improvements", "None required"),
        ],
    ),
    dict(
        filename = "prop1_deposit.jpg",
        title    = "DEPOSIT PROTECTION CERTIFICATE",
        doc_type = "deposit_protection",
        address  = "4 Birchwood Close, Harlow, CM17 0PQ",
        doc_name = "Deposit Protection Certificate - 4 Birchwood Close",
        fields   = [
            ("Property Address",   "4 Birchwood Close, Harlow, CM17 0PQ"),
            ("Tenant Name",        "James & Claire Whitfield"),
            ("Deposit Amount",     "GBP 1,295"),
            ("Protection Scheme",  "TDS (Tenancy Deposit Scheme)"),
            ("Certificate Number", "TDS-2022-441829"),
            ("Protection Date",    "18 September 2022"),
            ("Landlord",           "H. Patel"),
        ],
    ),
    dict(
        filename = "prop1_tenancy.jpg",
        title    = "ASSURED SHORTHOLD TENANCY AGREEMENT",
        doc_type = "tenancy_agreement",
        address  = "4 Birchwood Close, Harlow, CM17 0PQ",
        doc_name = "Tenancy Agreement - 4 Birchwood Close",
        fields   = [
            ("Property Address",    "4 Birchwood Close, Harlow, CM17 0PQ"),
            ("Tenant Full Name",    "James & Claire Whitfield"),
            ("Landlord",            "H. Patel"),
            ("Monthly Rent Amount", "GBP 1,295"),
            ("Tenancy Start Date",  "15 September 2022"),
            ("Tenancy End Date",    "14 September 2024"),
            ("Deposit Amount",      "GBP 1,295"),
            ("Break Clause",        "6 months"),
        ],
    ),
    dict(
        filename = "prop1_inventory.jpg",
        title    = "INVENTORY AND CHECK-IN REPORT",
        doc_type = "inventory",
        address  = "4 Birchwood Close, Harlow, CM17 0PQ",
        doc_name = "Inventory Check-in Report - 4 Birchwood Close",
        fields   = [
            ("Property Address", "4 Birchwood Close, Harlow, CM17 0PQ"),
            ("Inspection Date",  "15 September 2022"),
            ("Clerk",            "Premier Inventories Ltd"),
            ("Tenant",           "James & Claire Whitfield"),
            ("Overall Condition","Good throughout"),
            (None, None),
            ("## Room Conditions", None),
            ("Living Room",      "Good condition, no damage noted"),
            ("Kitchen",          "Good condition, all appliances present and working"),
            ("Bedroom 1",        "Good condition, furnishings present"),
            ("Bathroom",         "Good condition, no leaks or damage"),
        ],
    ),

    # =========================================================================
    # PROPERTY 2 -- 12 Rosebank Avenue, Epping  (all expiring within 60 days)
    # =========================================================================
    dict(
        filename = "prop2_gas_safety.jpg",
        title    = "GAS SAFETY CERTIFICATE (CP12)",
        doc_type = "gas_safety",
        address  = "12 Rosebank Avenue, Epping, CM16 5TR",
        doc_name = "Gas Safety Certificate - 12 Rosebank Avenue",
        fields   = [
            ("Property Address",      "12 Rosebank Avenue, Epping, CM16 5TR"),
            ("Engineer Name",         "SafeGas Essex"),
            ("Gas Safe Registration", "509122"),
            ("Inspection Date",       "18 April 2025"),
            ("Expiry Date",           "18 April 2026"),
            ("Result",                "PASS"),
            ("Tenant",                "Mohammed Al-Rashid"),
            ("Landlord",              "S. Okafor"),
        ],
    ),
    dict(
        filename = "prop2_eicr.jpg",
        title    = "ELECTRICAL INSTALLATION CONDITION REPORT (EICR)",
        doc_type = "eicr",
        address  = "12 Rosebank Avenue, Epping, CM16 5TR",
        doc_name = "EICR - 12 Rosebank Avenue",
        fields   = [
            ("Property Address",    "12 Rosebank Avenue, Epping, CM16 5TR"),
            ("Electrician",         "Voltex Electrical"),
            ("NICEIC Registration", "4422"),
            ("Inspection Date",     "12 May 2021"),
            ("Next Inspection Due", "12 May 2026"),
            ("Result",              "SATISFACTORY"),
            ("Observations",        "Recommend upgrade of consumer unit to comply with latest BS 7671"),
            ("Landlord",            "S. Okafor"),
        ],
    ),
    dict(
        filename = "prop2_epc.jpg",
        title    = "ENERGY PERFORMANCE CERTIFICATE (EPC)",
        doc_type = "epc",
        address  = "12 Rosebank Avenue, Epping, CM16 5TR",
        doc_name = "EPC - 12 Rosebank Avenue",
        fields   = [
            ("Property Address",     "12 Rosebank Avenue, Epping, CM16 5TR"),
            ("Current Energy Rating","C"),
            ("Energy Score",         "72"),
            ("Assessor",             "HomeSurvey Ltd"),
            ("Assessment Date",      "03 March 2019"),
            ("Valid Until",          "01 June 2026"),
            ("Primary Heating",      "Gas Central Heating"),
        ],
    ),
    dict(
        filename = "prop2_deposit.jpg",
        title    = "DEPOSIT PROTECTION CERTIFICATE",
        doc_type = "deposit_protection",
        address  = "12 Rosebank Avenue, Epping, CM16 5TR",
        doc_name = "Deposit Protection Certificate - 12 Rosebank Avenue",
        fields   = [
            ("Property Address",   "12 Rosebank Avenue, Epping, CM16 5TR"),
            ("Tenant Name",        "Mohammed Al-Rashid"),
            ("Deposit Amount",     "GBP 1,150"),
            ("Protection Scheme",  "MyDeposits"),
            ("Certificate Number", "MYD-2024-772014"),
            ("Protection Date",    "04 March 2024"),
            ("Landlord",           "S. Okafor"),
        ],
    ),
    dict(
        filename = "prop2_tenancy.jpg",
        title    = "ASSURED SHORTHOLD TENANCY AGREEMENT",
        doc_type = "tenancy_agreement",
        address  = "12 Rosebank Avenue, Epping, CM16 5TR",
        doc_name = "Tenancy Agreement - 12 Rosebank Avenue",
        fields   = [
            ("Property Address",    "12 Rosebank Avenue, Epping, CM16 5TR"),
            ("Tenant Full Name",    "Mohammed Al-Rashid"),
            ("Landlord",            "S. Okafor"),
            ("Monthly Rent Amount", "GBP 1,150"),
            ("Tenancy Start Date",  "01 March 2024"),
            ("Tenancy End Date",    "28 February 2026"),
            ("Deposit Amount",      "GBP 1,150"),
        ],
    ),

    # =========================================================================
    # PROPERTY 3 -- 7 Thornfield Road, Harlow  (all expired)
    # =========================================================================
    dict(
        filename = "prop3_gas_safety.jpg",
        title    = "GAS SAFETY CERTIFICATE (CP12)",
        doc_type = "gas_safety",
        address  = "7 Thornfield Road, Harlow, CM20 2BX",
        doc_name = "Gas Safety Certificate - 7 Thornfield Road",
        fields   = [
            ("Property Address",      "7 Thornfield Road, Harlow, CM20 2BX"),
            ("Engineer Name",         "Essex Gas Services"),
            ("Gas Safe Registration", "388812"),
            ("Inspection Date",       "08 January 2024"),
            ("Expiry Date",           "08 January 2025"),
            ("Result",                "PASS WITH ADVISORY"),
            ("Advisory Note",         "Pilot light on gas hob shows intermittent ignition — service within 3 months"),
            ("Tenant",                "Sandra & Kevin Obi"),
            ("Landlord",              "T. Brennan"),
        ],
    ),
    dict(
        filename = "prop3_eicr.jpg",
        title    = "ELECTRICAL INSTALLATION CONDITION REPORT (EICR)",
        doc_type = "eicr",
        address  = "7 Thornfield Road, Harlow, CM20 2BX",
        doc_name = "EICR - 7 Thornfield Road",
        fields   = [
            ("Property Address",    "7 Thornfield Road, Harlow, CM20 2BX"),
            ("Electrician",         "County Electrics"),
            ("NICEIC Registration", "3301"),
            ("Inspection Date",     "15 March 2019"),
            ("Next Inspection Due", "15 March 2024"),
            ("Result",              "SATISFACTORY"),
            ("Observations",        "Consumer unit older split-load type. Several sockets show age-related wear"),
            ("Landlord",            "T. Brennan"),
        ],
    ),
    dict(
        filename = "prop3_epc.jpg",
        title    = "ENERGY PERFORMANCE CERTIFICATE (EPC)",
        doc_type = "epc",
        address  = "7 Thornfield Road, Harlow, CM20 2BX",
        doc_name = "EPC - 7 Thornfield Road",
        fields   = [
            ("Property Address",     "7 Thornfield Road, Harlow, CM20 2BX"),
            ("Current Energy Rating","D"),
            ("Energy Score",         "58"),
            ("Assessor",             "SurveyCo"),
            ("Assessment Date",      "02 June 2014"),
            ("Valid Until",          "02 June 2024"),
            ("Primary Heating",      "Electric Storage Heaters"),
        ],
    ),
    dict(
        filename = "prop3_tenancy.jpg",
        title    = "ASSURED SHORTHOLD TENANCY AGREEMENT",
        doc_type = "tenancy_agreement",
        address  = "7 Thornfield Road, Harlow, CM20 2BX",
        doc_name = "Tenancy Agreement - 7 Thornfield Road",
        fields   = [
            ("Property Address",    "7 Thornfield Road, Harlow, CM20 2BX"),
            ("Tenant Full Name",    "Sandra & Kevin Obi"),
            ("Landlord",            "T. Brennan"),
            ("Monthly Rent Amount", "GBP 1,400"),
            ("Tenancy Start Date",  "01 June 2021"),
            ("Tenancy End Date",    "31 May 2023"),
            ("Deposit Amount",      "GBP 1,400"),
        ],
    ),

    # =========================================================================
    # PROPERTY 4 -- 23 Linnet Drive, Hoddesdon  (mixed / no deposit)
    # =========================================================================
    dict(
        filename = "prop4_gas_safety.jpg",
        title    = "GAS SAFETY CERTIFICATE (CP12)",
        doc_type = "gas_safety",
        address  = "23 Linnet Drive, Hoddesdon, EN11 9QR",
        doc_name = "Gas Safety Certificate - 23 Linnet Drive",
        fields   = [
            ("Property Address",      "23 Linnet Drive, Hoddesdon, EN11 9QR"),
            ("Engineer Name",         "SafeHeat Ltd"),
            ("Gas Safe Registration", "701234"),
            ("Inspection Date",       "14 February 2026"),
            ("Expiry Date",           "14 February 2027"),
            ("Result",                "PASS"),
            ("Tenant",                "Priya Nair"),
            ("Landlord",              "R. Gupta"),
        ],
    ),
    dict(
        filename = "prop4_eicr.jpg",
        title    = "ELECTRICAL INSTALLATION CONDITION REPORT (EICR)",
        doc_type = "eicr",
        address  = "23 Linnet Drive, Hoddesdon, EN11 9QR",
        doc_name = "EICR - 23 Linnet Drive",
        fields   = [
            ("Property Address",    "23 Linnet Drive, Hoddesdon, EN11 9QR"),
            ("Electrician",         "Spark Right"),
            ("NICEIC Registration", "8821"),
            ("Inspection Date",     "03 October 2023"),
            ("Next Inspection Due", "03 October 2028"),
            ("Result",              "SATISFACTORY"),
            ("Observations",        "C3 - Main switch labelling partially obscured, re-label circuits for clarity"),
            ("Landlord",            "R. Gupta"),
        ],
    ),
    dict(
        filename = "prop4_epc.jpg",
        title    = "ENERGY PERFORMANCE CERTIFICATE (EPC)",
        doc_type = "epc",
        address  = "23 Linnet Drive, Hoddesdon, EN11 9QR",
        doc_name = "EPC - 23 Linnet Drive",
        fields   = [
            ("Property Address",     "23 Linnet Drive, Hoddesdon, EN11 9QR"),
            ("Current Energy Rating","E"),
            ("Energy Score",         "42"),
            ("Assessor",             "BasicSurveys"),
            ("Assessment Date",      "05 November 2018"),
            ("Valid Until",          "05 November 2023"),
            ("Primary Heating",      "Electric Panel Heaters"),
        ],
    ),
    dict(
        filename = "prop4_tenancy.jpg",
        title    = "ASSURED SHORTHOLD TENANCY AGREEMENT",
        doc_type = "tenancy_agreement",
        address  = "23 Linnet Drive, Hoddesdon, EN11 9QR",
        doc_name = "Tenancy Agreement - 23 Linnet Drive",
        fields   = [
            ("Property Address",    "23 Linnet Drive, Hoddesdon, EN11 9QR"),
            ("Tenant Full Name",    "Priya Nair"),
            ("Landlord",            "R. Gupta"),
            ("Monthly Rent Amount", "GBP 1,050"),
            ("Tenancy Start Date",  "01 November 2023"),
            ("Tenancy End Date",    "31 October 2025"),
            ("Deposit Amount",      "GBP 1,050"),
        ],
    ),

    # =========================================================================
    # PROPERTY 5 -- 9 Coppice Lane, Bishops Stortford  (sparse: 2 docs only)
    # =========================================================================
    dict(
        filename = "prop5_gas_safety.jpg",
        title    = "GAS SAFETY CERTIFICATE (CP12)",
        doc_type = "gas_safety",
        address  = "9 Coppice Lane, Bishops Stortford, CM23 4HH",
        doc_name = "Gas Safety Certificate - 9 Coppice Lane",
        fields   = [
            ("Property Address",      "9 Coppice Lane, Bishops Stortford, CM23 4HH"),
            ("Engineer Name",         "Premier Gas"),
            ("Gas Safe Registration", "445521"),
            ("Inspection Date",       "22 January 2026"),
            ("Expiry Date",           "22 January 2027"),
            ("Result",                "PASS"),
            ("Landlord",              "F. Andersen"),
        ],
    ),
    dict(
        filename = "prop5_tenancy.jpg",
        title    = "ASSURED SHORTHOLD TENANCY AGREEMENT",
        doc_type = "tenancy_agreement",
        address  = "9 Coppice Lane, Bishops Stortford, CM23 4HH",
        doc_name = "Tenancy Agreement - 9 Coppice Lane",
        fields   = [
            ("Property Address",    "9 Coppice Lane, Bishops Stortford, CM23 4HH"),
            ("Tenant Full Name",    "To Be Confirmed"),
            ("Landlord",            "F. Andersen"),
            ("Monthly Rent Amount", "GBP 1,100"),
            ("Tenancy Start Date",  "01 February 2026"),
            ("Tenancy End Date",    "31 January 2027"),
            ("Deposit Amount",      "GBP 1,100"),
        ],
    ),

    # =========================================================================
    # PROPERTY 6 -- 31 Mallard Way, Epping  (all AI prefilled -- none verified)
    # =========================================================================
    dict(
        filename = "prop6_gas_safety.jpg",
        title    = "GAS SAFETY CERTIFICATE (CP12)",
        doc_type = "gas_safety",
        address  = "31 Mallard Way, Epping, CM16 7RN",
        doc_name = "Gas Safety Certificate - 31 Mallard Way",
        fields   = [
            ("Property Address",      "31 Mallard Way, Epping, CM16 7RN"),
            ("Engineer Name",         "AllGas UK"),
            ("Gas Safe Registration", "523001"),
            ("Inspection Date",       "15 July 2025"),
            ("Expiry Date",           "15 July 2026"),
            ("Result",                "PASS"),
            ("Tenant",                "George & Irene Kowalski"),
            ("Landlord",              "M. Nowak"),
        ],
    ),
    dict(
        filename = "prop6_eicr.jpg",
        title    = "ELECTRICAL INSTALLATION CONDITION REPORT (EICR)",
        doc_type = "eicr",
        address  = "31 Mallard Way, Epping, CM16 7RN",
        doc_name = "EICR - 31 Mallard Way",
        fields   = [
            ("Property Address",    "31 Mallard Way, Epping, CM16 7RN"),
            ("Electrician",         "PowerCheck Ltd"),
            ("NICEIC Registration", "6612"),
            ("Inspection Date",     "08 August 2023"),
            ("Next Inspection Due", "08 August 2028"),
            ("Result",              "SATISFACTORY"),
            ("Observations",        "C3 - Recommend CO detector in kitchen. Outdoor socket needs weatherproof cover"),
            ("Landlord",            "M. Nowak"),
        ],
    ),
    dict(
        filename = "prop6_epc.jpg",
        title    = "ENERGY PERFORMANCE CERTIFICATE (EPC)",
        doc_type = "epc",
        address  = "31 Mallard Way, Epping, CM16 7RN",
        doc_name = "EPC - 31 Mallard Way",
        fields   = [
            ("Property Address",     "31 Mallard Way, Epping, CM16 7RN"),
            ("Current Energy Rating","C"),
            ("Energy Score",         "68"),
            ("Assessor",             "GreenRate"),
            ("Assessment Date",      "10 August 2023"),
            ("Valid Until",          "10 August 2033"),
            ("Primary Heating",      "Gas Central Heating"),
        ],
    ),
    dict(
        filename = "prop6_deposit.jpg",
        title    = "DEPOSIT PROTECTION CERTIFICATE",
        doc_type = "deposit_protection",
        address  = "31 Mallard Way, Epping, CM16 7RN",
        doc_name = "Deposit Protection Certificate - 31 Mallard Way",
        fields   = [
            ("Property Address",   "31 Mallard Way, Epping, CM16 7RN"),
            ("Tenant Name",        "George & Irene Kowalski"),
            ("Deposit Amount",     "GBP 1,375"),
            ("Protection Scheme",  "DPS (Deposit Protection Service)"),
            ("Certificate Number", "DPS-2023-991234"),
            ("Protection Date",    "03 August 2023"),
            ("Landlord",           "M. Nowak"),
        ],
    ),
    dict(
        filename = "prop6_tenancy.jpg",
        title    = "ASSURED SHORTHOLD TENANCY AGREEMENT",
        doc_type = "tenancy_agreement",
        address  = "31 Mallard Way, Epping, CM16 7RN",
        doc_name = "Tenancy Agreement - 31 Mallard Way",
        fields   = [
            ("Property Address",    "31 Mallard Way, Epping, CM16 7RN"),
            ("Tenant Full Name",    "George & Irene Kowalski"),
            ("Landlord",            "M. Nowak"),
            ("Monthly Rent Amount", "GBP 1,375"),
            ("Tenancy Start Date",  "01 August 2023"),
            ("Tenancy End Date",    "31 July 2025"),
            ("Deposit Amount",      "GBP 1,375"),
        ],
    ),
    dict(
        filename = "prop6_inventory.jpg",
        title    = "INVENTORY AND CHECK-IN REPORT",
        doc_type = "inventory",
        address  = "31 Mallard Way, Epping, CM16 7RN",
        doc_name = "Inventory Check-in Report - 31 Mallard Way",
        fields   = [
            ("Property Address", "31 Mallard Way, Epping, CM16 7RN"),
            ("Inspection Date",  "01 August 2023"),
            ("Clerk",            "CheckIn Pro"),
            ("Tenant",           "George & Irene Kowalski"),
            ("Overall Condition","Good"),
            (None, None),
            ("## Room Conditions", None),
            ("Living Room",      "Good"),
            ("Kitchen",          "Good"),
            ("Bedroom 1",        "Good"),
            ("Bathroom",         "Good"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    total = len(DOCS)
    ok, errors = [], []
    by_prop = {}

    print()
    print("  MorphIQ Test Document Generator -- JPEG Edition")
    print(f"  Client : {CLIENT_NAME}")
    print(f"  Output : {RAW_DIR}")
    print(f"  Total  : {total} documents")
    print()

    for i, doc in enumerate(DOCS, 1):
        out = RAW_DIR / doc["filename"]
        try:
            render_doc(doc["title"], doc["fields"], out)
            write_meta(out, doc["address"], doc["doc_name"], doc["doc_type"])
            kb = out.stat().st_size // 1024
            ok.append(doc["filename"])
            by_prop.setdefault(doc["address"], []).append(doc["doc_type"])
            print(f"  [{i:02d}/{total}] OK   {doc['filename']}  ({kb} KB)")
        except Exception as exc:
            errors.append((doc["filename"], str(exc)))
            print(f"  [{i:02d}/{total}] ERR  {doc['filename']}  -- {exc}")

    print()
    print("-" * 60)
    print(f"  COMPLETE: {len(ok)} JPEGs created, {len(errors)} errors")
    print()

    print("  Properties:")
    for addr, types in by_prop.items():
        print(f"    {addr}")
        for t in types:
            print(f"      * {t}")
    print()

    jpg_count  = len(list(RAW_DIR.glob("*.jpg")))
    meta_count = len(list(RAW_DIR.glob("*.meta.json")))
    print(f"  Verification: {jpg_count} JPEGs, {meta_count} meta.json files in output folder")
    print(f"  Folder: {RAW_DIR}")
    print()

    if errors:
        print("  ERRORS:")
        for fn, err in errors:
            print(f"    {fn}: {err}")
        print()

    if jpg_count != total or meta_count != total:
        print(f"  WARNING: expected {total} of each -- got {jpg_count} JPEGs / {meta_count} metas")
        sys.exit(1)


if __name__ == "__main__":
    main()
