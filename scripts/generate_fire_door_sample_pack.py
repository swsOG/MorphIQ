from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "test_data"
JPG_PATH = OUT_DIR / "fire_door_certificate_clean.jpg"
PDF_PATH = OUT_DIR / "fire_door_certificate_clean.pdf"


def _font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def build_jpg() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1654, 2339), "white")
    draw = ImageDraw.Draw(image)

    title_font = _font(74, bold=True)
    section_font = _font(42, bold=True)
    body_font = _font(34)
    strong_font = _font(34, bold=True)

    navy = "#24364B"
    text = "#17212F"
    muted = "#5A6778"
    line = "#D6DCE5"
    success = "#1E7A46"

    draw.rounded_rectangle((110, 110, 1544, 320), radius=20, fill=navy)
    draw.text((160, 150), "FIRE DOOR INSPECTION CERTIFICATE", font=title_font, fill="white")
    draw.text((160, 240), "Prepared for MorphIQ intake testing", font=body_font, fill="#DCE7F4")

    fields = [
        ("Property Address", "12 Oak Street, Epping, Essex CM16 4PT"),
        ("Certificate Number", "FDC-2026-0417"),
        ("Door Location", "Ground Floor Lobby Entrance"),
        ("Inspection Date", "17 April 2026"),
        ("Next Inspection Date", "17 October 2026"),
        ("Result", "PASS"),
    ]

    y = 410
    for label, value in fields:
        draw.text((140, y), label, font=strong_font, fill=muted)
        draw.text((560, y), value, font=body_font, fill=success if label == "Result" else text)
        draw.line((140, y + 52, 1510, y + 52), fill=line, width=3)
        y += 110

    draw.text((140, 1130), "Inspection Notes", font=section_font, fill=navy)
    notes = [
        "Door closer operational and secure.",
        "Intumescent strips present and continuous.",
        "Cold smoke seals intact along frame.",
        "No visible damage affecting fire performance.",
    ]
    y = 1210
    for note in notes:
        draw.ellipse((148, y + 12, 166, y + 30), fill=navy)
        draw.text((190, y), note, font=body_font, fill=text)
        y += 78

    draw.text((140, 1640), "Inspector", font=section_font, fill=navy)
    draw.text((140, 1720), "Name", font=strong_font, fill=muted)
    draw.text((360, 1720), "Amelia Hart", font=body_font, fill=text)
    draw.text((140, 1805), "Company", font=strong_font, fill=muted)
    draw.text((360, 1805), "Essex Fire Compliance Ltd", font=body_font, fill=text)
    draw.text((140, 1890), "Inspector ID", font=strong_font, fill=muted)
    draw.text((360, 1890), "EFC-4421", font=body_font, fill=text)

    draw.rounded_rectangle((110, 2070, 1544, 2235), radius=18, outline=line, width=4)
    draw.text((140, 2110), "This is a synthetic sample document for Fire Door Certificate testing.", font=body_font, fill=text)
    draw.text((140, 2170), "Use this JPG or the matching PDF in ScanStation import mode.", font=body_font, fill=text)

    image.save(JPG_PATH, quality=95)


def build_pdf() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    width, height = A4
    c = canvas.Canvas(str(PDF_PATH), pagesize=A4)

    navy = HexColor("#24364B")
    text = HexColor("#17212F")
    muted = HexColor("#5A6778")
    line = HexColor("#D6DCE5")
    success = HexColor("#1E7A46")

    c.setFillColor(navy)
    c.roundRect(36, height - 120, width - 72, 82, 10, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(54, height - 78, "FIRE DOOR INSPECTION CERTIFICATE")
    c.setFont("Helvetica", 11)
    c.drawString(54, height - 98, "Prepared for MorphIQ intake testing")

    rows = [
        ("Property Address", "12 Oak Street, Epping, Essex CM16 4PT"),
        ("Certificate Number", "FDC-2026-0417"),
        ("Door Location", "Ground Floor Lobby Entrance"),
        ("Inspection Date", "17 April 2026"),
        ("Next Inspection Date", "17 October 2026"),
        ("Result", "PASS"),
    ]
    y = height - 165
    for label, value in rows:
        c.setFillColor(muted)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(42, y, label)
        c.setFillColor(success if label == "Result" else text)
        c.setFont("Helvetica", 11)
        c.drawString(185, y, value)
        c.setStrokeColor(line)
        c.setLineWidth(1)
        c.line(42, y - 10, width - 42, y - 10)
        y -= 38

    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(42, y - 10, "Inspection Notes")
    y -= 35
    c.setFillColor(text)
    c.setFont("Helvetica", 11)
    for note in [
        "Door closer operational and secure.",
        "Intumescent strips present and continuous.",
        "Cold smoke seals intact along frame.",
        "No visible damage affecting fire performance.",
    ]:
        c.drawString(54, y, f"- {note}")
        y -= 22

    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(42, y - 10, "Inspector")
    y -= 38
    c.setFillColor(text)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(42, y, "Name")
    c.setFont("Helvetica", 11)
    c.drawString(155, y, "Amelia Hart")
    y -= 22
    c.setFont("Helvetica-Bold", 11)
    c.drawString(42, y, "Company")
    c.setFont("Helvetica", 11)
    c.drawString(155, y, "Essex Fire Compliance Ltd")
    y -= 22
    c.setFont("Helvetica-Bold", 11)
    c.drawString(42, y, "Inspector ID")
    c.setFont("Helvetica", 11)
    c.drawString(155, y, "EFC-4421")

    c.setStrokeColor(line)
    c.roundRect(36, 52, width - 72, 54, 8, fill=0, stroke=1)
    c.setFillColor(text)
    c.setFont("Helvetica", 10)
    c.drawString(50, 84, "Synthetic Fire Door Certificate sample for ScanStation import testing.")
    c.drawString(50, 67, "Pair this PDF with fire_door_certificate_clean.jpg for end-to-end checks.")

    c.showPage()
    c.save()


if __name__ == "__main__":
    build_jpg()
    build_pdf()
    print(JPG_PATH)
    print(PDF_PATH)
