"""
Batch 1: Generate 35 Assured Shorthold Tenancy Agreement PDFs
Uses shared data from data.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from data import *
import os
from datetime import datetime, timedelta
import csv
import random

# Ensure output directory exists
os.makedirs('test_documents', exist_ok=True)

def generate_reference_number(agency_name, year, sequence):
    """Generate realistic reference numbers based on agency"""
    if "Belmont" in agency_name:
        return f"BEL-AST-{year}-{sequence:04d}"
    elif "Crown" in agency_name:
        return f"CRE-{year}-{sequence:03d}"
    elif "Harlow" in agency_name:
        return f"HPM/AST/{year}/{sequence:03d}"
    elif "Premier" in agency_name:
        return f"PLS-T-{year}-{sequence:04d}"
    elif "Alexander" in agency_name:
        return f"AH-{year}-{sequence:04d}"
    else:
        return f"AST/{year}/{sequence:03d}"

def get_standard_terms():
    """Return standard AST terms and conditions"""
    return [
        ("Rent Payment", "The Tenant shall pay the Rent on or before the Rent Payment Date each month by the agreed method. Late payment may incur interest charges at 3% above Bank of England base rate."),
        ("Use of Property", "The Property shall be used as a private dwelling only and for no other purpose. The Tenant shall not carry on any business, profession or trade from the Property without prior written consent."),
        ("Repairs and Maintenance", "The Landlord shall keep in repair the structure and exterior of the Property and keep in working order the installations for supply of water, gas, electricity, sanitation, and heating. The Tenant shall keep the interior in good condition."),
        ("Alterations", "The Tenant shall not make any alterations or additions to the Property without the prior written consent of the Landlord."),
        ("Assignment and Subletting", "The Tenant shall not assign, sublet or part with possession of the Property or any part thereof without the prior written consent of the Landlord."),
        ("Access", "The Tenant shall permit the Landlord or their agents to enter the Property at reasonable times of the day upon giving at least 24 hours written notice (except in emergency) to inspect the condition or carry out repairs."),
        ("Utilities", "The Tenant shall pay all charges for gas, electricity, water, telephone, internet, and council tax during the tenancy."),
        ("Insurance", "The Landlord shall insure the building. The Tenant is responsible for insuring their own contents and belongings."),
        ("Ending the Tenancy", "Either party may end this agreement by giving at least two months written notice after the end of the fixed term. During the fixed term, the agreement can only be ended by mutual consent or as provided by law."),
    ]

def add_break_clause():
    """Return optional break clause"""
    return ("Break Clause", "Either party may terminate this agreement after 6 months of the fixed term by giving at least 2 months written notice in writing to the other party.")

def add_guarantor_clause(guarantor_name):
    """Return guarantor clause"""
    return ("Guarantor", f"The Guarantor, {guarantor_name}, guarantees the performance of the Tenant's obligations under this agreement and agrees to pay any rent arrears or damages if the Tenant fails to do so.")

# Style 1: Agency-branded formal
def create_agency_branded_ast(filename, data):
    """Create agency-branded formal style AST"""
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Page 1
    # Header bar
    agency_color = colors.HexColor('#1a5490') if 'Belmont' in data['agency'] else colors.HexColor('#2d5016')
    c.setFillColor(agency_color)
    c.rect(0, height - 80, width, 80, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 45, data['agency'])
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 62, data['agency_address'])

    # Title
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 110, "ASSURED SHORTHOLD TENANCY AGREEMENT")

    c.setFont("Helvetica", 9)
    c.drawString(450, height - 110, f"Ref: {data['reference']}")

    # Section headers with colored background
    y = height - 150

    def draw_section_header(title, y_pos):
        c.setFillColor(agency_color)
        c.rect(40, y_pos - 15, width - 80, 20, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y_pos - 10, title)
        c.setFillColor(colors.black)
        return y_pos - 35

    # Parties section
    y = draw_section_header("THE PARTIES", y)
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Landlord: {data['landlord_name']}")
    c.drawString(50, y - 15, f"Address: {data['landlord_address']}")

    y -= 35
    tenant_text = f"Tenant(s): {data['tenant_names']}"
    c.drawString(50, y, tenant_text)
    if data.get('tenant_email'):
        c.drawString(50, y - 15, f"Email: {data['tenant_email']}")
        y -= 15
    if data.get('tenant_phone'):
        c.drawString(50, y - 15, f"Phone: {data['tenant_phone']}")
        y -= 15

    y -= 25

    # Property section
    y = draw_section_header("THE PROPERTY", y)
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Address: {data['property_address']}")
    c.drawString(50, y - 15, f"Type: {data['property_type']} | Furnished: {data['furnished']}")

    y -= 40

    # Tenancy Details section
    y = draw_section_header("TENANCY DETAILS", y)
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Start Date: {data['start_date']}")
    c.drawString(50, y - 15, f"End Date: {data['end_date']}")
    c.drawString(50, y - 30, f"Fixed Term: {data['term_months']} months")

    y -= 50

    # Financial section
    y = draw_section_header("FINANCIAL TERMS", y)
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Monthly Rent: £{data['monthly_rent']:,.2f}")
    c.drawString(50, y - 15, f"Deposit: £{data['deposit']:,.2f}")
    c.drawString(50, y - 30, f"Deposit Protection: {data['deposit_scheme']}")
    c.drawString(50, y - 45, f"Rent Payment Date: {data['rent_day']} of each month")
    c.drawString(50, y - 60, f"Payment Method: {data['payment_method']}")

    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(50, 30, f"Page 1 of {data['total_pages']}")
    c.drawRightString(width - 50, 30, f"Generated: {data['agreement_date']}")

    c.showPage()

    # Page 2 - Terms and Conditions
    y = height - 60
    y = draw_section_header("TERMS AND CONDITIONS", y)

    c.setFont("Helvetica", 10)
    terms = data['terms']

    for idx, (title, text) in enumerate(terms[:6], 1):
        if y < 120:
            c.showPage()
            y = height - 60

        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, f"{idx}. {title}")
        y -= 15

        c.setFont("Helvetica", 9)
        # Wrap text
        words = text.split()
        line = ""
        for word in words:
            if c.stringWidth(line + " " + word, "Helvetica", 9) < width - 120:
                line += " " + word if line else word
            else:
                c.drawString(60, y, line)
                y -= 12
                line = word
                if y < 100:
                    c.showPage()
                    y = height - 60
        if line:
            c.drawString(60, y, line)
            y -= 20

    c.setFont("Helvetica", 8)
    c.drawString(50, 30, f"Page 2 of {data['total_pages']}")

    c.showPage()

    # Page 3 - More terms and signatures
    y = height - 60

    for idx, (title, text) in enumerate(terms[6:], 7):
        if y < 180:
            break

        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, f"{idx}. {title}")
        y -= 15

        c.setFont("Helvetica", 9)
        words = text.split()
        line = ""
        for word in words:
            if c.stringWidth(line + " " + word, "Helvetica", 9) < width - 120:
                line += " " + word if line else word
            else:
                c.drawString(60, y, line)
                y -= 12
                line = word
        if line:
            c.drawString(60, y, line)
            y -= 20

    # Signatures
    y -= 20
    y = draw_section_header("SIGNATURES", y)

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Signed on: {data['agreement_date']}")

    y -= 40
    c.drawString(50, y, "Landlord:")
    c.line(120, y - 5, 300, y - 5)
    c.drawString(50, y - 20, f"Print: {data['landlord_name']}")

    y -= 60
    c.drawString(50, y, "Tenant(s):")
    c.line(120, y - 5, 300, y - 5)
    c.drawString(50, y - 20, f"Print: {data['tenant_names']}")

    y -= 60
    c.drawString(50, y, "Witness:")
    c.line(120, y - 5, 300, y - 5)

    c.setFont("Helvetica", 8)
    c.drawString(50, 30, f"Page 3 of {data['total_pages']}")

    c.save()

# Style 2: Traditional legal style
def create_traditional_legal_ast(filename, data):
    """Create traditional legal bordered style AST"""
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Page 1
    # Border
    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    c.rect(30, 30, width - 60, height - 60, fill=False, stroke=True)

    # Title
    c.setFont("Times-Bold", 18)
    c.drawCentredString(width/2, height - 70, "ASSURED SHORTHOLD TENANCY AGREEMENT")

    c.setFont("Times-Roman", 10)
    c.drawCentredString(width/2, height - 95, f"Reference: {data['reference']}")

    # Legal preamble
    y = height - 130
    c.setFont("Times-Bold", 11)
    c.drawString(50, y, "THIS AGREEMENT is made on")
    c.setFont("Times-Roman", 11)
    c.drawString(260, y, f"{data['agreement_date']}")

    y -= 30
    c.setFont("Times-Bold", 11)
    c.drawString(50, y, "BETWEEN:")

    y -= 25
    c.setFont("Times-Roman", 11)
    c.drawString(70, y, f"{data['landlord_name']} of {data['landlord_address']}")
    c.drawString(70, y - 15, '(hereinafter called "the Landlord")')

    y -= 45
    c.setFont("Times-Bold", 11)
    c.drawString(50, y, "AND:")

    y -= 25
    c.setFont("Times-Roman", 11)
    c.drawString(70, y, f"{data['tenant_names']}")
    c.drawString(70, y - 15, '(hereinafter called "the Tenant")')

    y -= 45
    c.setFont("Times-Bold", 11)
    c.drawString(50, y, "IN RESPECT OF:")

    y -= 25
    c.setFont("Times-Roman", 11)
    c.drawString(70, y, f"{data['property_address']}")
    c.drawString(70, y - 15, f"({data['property_type']}, {data['furnished']})")
    c.drawString(70, y - 30, '(hereinafter called "the Property")')

    y -= 55
    c.setFont("Times-Bold", 11)
    c.drawString(50, y, "IT IS AGREED as follows:")

    y -= 30
    c.setFont("Times-Bold", 10)
    c.drawString(50, y, "1. TERM")
    y -= 15
    c.setFont("Times-Roman", 10)
    c.drawString(60, y, f"The tenancy shall commence on {data['start_date']} and continue for a fixed term")
    c.drawString(60, y - 12, f"of {data['term_months']} months until {data['end_date']}.")

    y -= 35
    c.setFont("Times-Bold", 10)
    c.drawString(50, y, "2. RENT")
    y -= 15
    c.setFont("Times-Roman", 10)
    c.drawString(60, y, f"The Tenant shall pay rent of £{data['monthly_rent']:,.2f} per calendar month,")
    c.drawString(60, y - 12, f"payable in advance on the {data['rent_day']} day of each month by {data['payment_method']}.")

    y -= 35
    c.setFont("Times-Bold", 10)
    c.drawString(50, y, "3. DEPOSIT")
    y -= 15
    c.setFont("Times-Roman", 10)
    c.drawString(60, y, f"The Tenant has paid a deposit of £{data['deposit']:,.2f} which will be protected under")
    c.drawString(60, y - 12, f"the {data['deposit_scheme']}.")

    c.setFont("Times-Roman", 8)
    c.drawCentredString(width/2, 40, f"Page 1 of {data['total_pages']}")

    c.showPage()

    # Page 2
    c.rect(30, 30, width - 60, height - 60, fill=False, stroke=True)

    y = height - 60
    c.setFont("Times-Bold", 12)
    c.drawString(50, y, "TENANT'S OBLIGATIONS")

    y -= 25
    for idx, (title, text) in enumerate(data['terms'][:7], 4):
        if y < 100:
            c.setFont("Times-Roman", 8)
            c.drawCentredString(width/2, 40, f"Page 2 of {data['total_pages']}")
            c.showPage()
            c.rect(30, 30, width - 60, height - 60, fill=False, stroke=True)
            y = height - 60

        c.setFont("Times-Bold", 10)
        c.drawString(50, y, f"{idx}. {title.upper()}")
        y -= 15

        c.setFont("Times-Roman", 9)
        words = text.split()
        line = ""
        for word in words:
            if c.stringWidth(line + " " + word, "Times-Roman", 9) < width - 120:
                line += " " + word if line else word
            else:
                c.drawString(60, y, line)
                y -= 11
                line = word
        if line:
            c.drawString(60, y, line)
            y -= 20

    c.setFont("Times-Roman", 8)
    c.drawCentredString(width/2, 40, f"Page 2 of {data['total_pages']}")

    c.showPage()

    # Page 3 - Signatures
    c.rect(30, 30, width - 60, height - 60, fill=False, stroke=True)

    y = height - 60

    for idx, (title, text) in enumerate(data['terms'][7:], 11):
        if y < 250:
            break

        c.setFont("Times-Bold", 10)
        c.drawString(50, y, f"{idx}. {title.upper()}")
        y -= 15

        c.setFont("Times-Roman", 9)
        words = text.split()
        line = ""
        for word in words:
            if c.stringWidth(line + " " + word, "Times-Roman", 9) < width - 120:
                line += " " + word if line else word
            else:
                c.drawString(60, y, line)
                y -= 11
                line = word
        if line:
            c.drawString(60, y, line)
            y -= 20

    y -= 20
    c.setFont("Times-Bold", 11)
    c.drawString(50, y, "SIGNED by the parties:")

    y -= 40
    c.setFont("Times-Roman", 10)
    c.drawString(50, y, "LANDLORD:")
    c.line(140, y - 3, 350, y - 3)
    c.drawString(50, y - 25, f"Name: {data['landlord_name']}")
    c.drawString(50, y - 40, f"Date: {data['agreement_date']}")

    y -= 80
    c.drawString(50, y, "TENANT:")
    c.line(140, y - 3, 350, y - 3)
    c.drawString(50, y - 25, f"Name: {data['tenant_names']}")
    c.drawString(50, y - 40, f"Date: {data['agreement_date']}")

    y -= 80
    c.drawString(50, y, "WITNESS:")
    c.line(140, y - 3, 350, y - 3)
    c.drawString(50, y - 25, "Name:")
    c.drawString(50, y - 40, f"Date: {data['agreement_date']}")

    c.setFont("Times-Roman", 8)
    c.drawCentredString(width/2, 40, f"Page 3 of {data['total_pages']}")

    c.save()

# Style 3: Simple modern
def create_simple_modern_ast(filename, data):
    """Create simple modern clean style AST"""
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Page 1
    # Simple header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 60, "Tenancy Agreement")

    c.setFont("Helvetica", 9)
    c.drawRightString(width - 50, height - 60, f"Ref: {data['reference']}")
    c.drawRightString(width - 50, height - 75, f"Date: {data['agreement_date']}")

    # Clean divider
    c.setStrokeColor(colors.HexColor('#333333'))
    c.setLineWidth(0.5)
    c.line(50, height - 85, width - 50, height - 85)

    y = height - 110

    # Field-based layout
    def draw_field(label, value, y_pos):
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor('#666666'))
        c.drawString(50, y_pos, label)
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawString(180, y_pos, value)
        return y_pos - 18

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Landlord Information")
    y -= 25

    y = draw_field("Name:", data['landlord_name'], y)
    y = draw_field("Address:", data['landlord_address'], y)

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Tenant Information")
    y -= 25

    y = draw_field("Name(s):", data['tenant_names'], y)
    if data.get('tenant_email'):
        y = draw_field("Email:", data['tenant_email'], y)
    if data.get('tenant_phone'):
        y = draw_field("Phone:", data['tenant_phone'], y)

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Property Details")
    y -= 25

    y = draw_field("Address:", data['property_address'], y)
    y = draw_field("Type:", data['property_type'], y)
    y = draw_field("Furnished:", data['furnished'], y)

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Tenancy Terms")
    y -= 25

    y = draw_field("Start Date:", data['start_date'], y)
    y = draw_field("End Date:", data['end_date'], y)
    y = draw_field("Fixed Term:", f"{data['term_months']} months", y)

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Financial Details")
    y -= 25

    y = draw_field("Monthly Rent:", f"£{data['monthly_rent']:,.2f}", y)
    y = draw_field("Deposit:", f"£{data['deposit']:,.2f}", y)
    y = draw_field("Deposit Protection:", data['deposit_scheme'], y)
    y = draw_field("Payment Date:", f"{data['rent_day']} of each month", y)
    y = draw_field("Payment Method:", data['payment_method'], y)

    if data.get('agency'):
        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Managing Agent")
        y -= 25
        y = draw_field("Agency:", data['agency'], y)
        y = draw_field("Address:", data['agency_address'], y)

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor('#999999'))
    c.drawString(50, 30, f"Page 1 of {data['total_pages']}")

    c.showPage()

    # Page 2 - Terms
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.black)
    c.drawString(50, height - 60, "Terms and Conditions")

    c.setLineWidth(0.5)
    c.line(50, height - 70, width - 50, height - 70)

    y = height - 95

    for idx, (title, text) in enumerate(data['terms'], 1):
        if y < 100:
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.HexColor('#999999'))
            c.drawString(50, 30, f"Page 2 of {data['total_pages']}")
            c.showPage()
            y = height - 60

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.black)
        c.drawString(50, y, f"{idx}. {title}")
        y -= 18

        c.setFont("Helvetica", 9)
        words = text.split()
        line = ""
        for word in words:
            if c.stringWidth(line + " " + word, "Helvetica", 9) < width - 100:
                line += " " + word if line else word
            else:
                c.drawString(60, y, line)
                y -= 12
                line = word
        if line:
            c.drawString(60, y, line)
            y -= 22

    # Signatures
    if y < 200:
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor('#999999'))
        c.drawString(50, 30, f"Page 2 of {data['total_pages']}")
        c.showPage()
        y = height - 60

    y -= 20
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.black)
    c.drawString(50, y, "Signatures")

    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "Landlord Signature:")
    c.line(160, y - 3, 350, y - 3)
    c.drawString(400, y, "Date:")
    c.line(440, y - 3, 545, y - 3)

    y -= 30
    c.drawString(50, y, "Tenant Signature:")
    c.line(160, y - 3, 350, y - 3)
    c.drawString(400, y, "Date:")
    c.line(440, y - 3, 545, y - 3)

    y -= 30
    c.drawString(50, y, "Witness Signature:")
    c.line(160, y - 3, 350, y - 3)
    c.drawString(400, y, "Date:")
    c.line(440, y - 3, 545, y - 3)

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor('#999999'))
    page_num = 3 if data['total_pages'] == 3 else 2
    c.drawString(50, 30, f"Page {page_num} of {data['total_pages']}")

    c.save()

# Style 4: Basic landlord-produced
def create_basic_landlord_ast(filename, data):
    """Create basic plain landlord-produced style AST"""
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Page 1
    # Very simple header
    c.setFont("Courier-Bold", 14)
    c.drawCentredString(width/2, height - 60, "ASSURED SHORTHOLD TENANCY AGREEMENT")

    c.setFont("Courier", 10)
    c.drawCentredString(width/2, height - 80, f"Reference: {data['reference']}")

    y = height - 110

    c.setFont("Courier-Bold", 11)
    c.drawString(50, y, "LANDLORD:")
    y -= 18
    c.setFont("Courier", 10)
    c.drawString(70, y, data['landlord_name'])
    c.drawString(70, y - 14, data['landlord_address'])

    y -= 40
    c.setFont("Courier-Bold", 11)
    c.drawString(50, y, "TENANT(S):")
    y -= 18
    c.setFont("Courier", 10)
    c.drawString(70, y, data['tenant_names'])
    if data.get('tenant_email'):
        c.drawString(70, y - 14, f"Email: {data['tenant_email']}")
        y -= 14
    if data.get('tenant_phone'):
        c.drawString(70, y - 14, f"Phone: {data['tenant_phone']}")
        y -= 14

    y -= 30
    c.setFont("Courier-Bold", 11)
    c.drawString(50, y, "PROPERTY:")
    y -= 18
    c.setFont("Courier", 10)
    c.drawString(70, y, data['property_address'])
    c.drawString(70, y - 14, f"{data['property_type']} - {data['furnished']}")

    y -= 40
    c.setFont("Courier-Bold", 11)
    c.drawString(50, y, "TERM:")
    y -= 18
    c.setFont("Courier", 10)
    c.drawString(70, y, f"Start: {data['start_date']}")
    c.drawString(70, y - 14, f"End: {data['end_date']}")
    c.drawString(70, y - 28, f"Fixed period: {data['term_months']} months")

    y -= 54
    c.setFont("Courier-Bold", 11)
    c.drawString(50, y, "RENT:")
    y -= 18
    c.setFont("Courier", 10)
    c.drawString(70, y, f"Monthly rent: £{data['monthly_rent']:,.2f}")
    c.drawString(70, y - 14, f"Payment due: {data['rent_day']} of each month")
    c.drawString(70, y - 28, f"Method: {data['payment_method']}")

    y -= 54
    c.setFont("Courier-Bold", 11)
    c.drawString(50, y, "DEPOSIT:")
    y -= 18
    c.setFont("Courier", 10)
    c.drawString(70, y, f"Amount: £{data['deposit']:,.2f}")
    c.drawString(70, y - 14, f"Protected by: {data['deposit_scheme']}")

    c.setFont("Courier", 8)
    c.drawString(50, 30, f"Page 1 of {data['total_pages']}")

    c.showPage()

    # Page 2 - Terms
    y = height - 60
    c.setFont("Courier-Bold", 12)
    c.drawString(50, y, "TERMS AND CONDITIONS:")

    y -= 30

    for idx, (title, text) in enumerate(data['terms'], 1):
        if y < 100:
            c.setFont("Courier", 8)
            c.drawString(50, 30, f"Page 2 of {data['total_pages']}")
            c.showPage()
            y = height - 60

        c.setFont("Courier-Bold", 10)
        c.drawString(50, y, f"{idx}. {title}")
        y -= 16

        c.setFont("Courier", 9)
        words = text.split()
        line = ""
        for word in words:
            test_line = line + " " + word if line else word
            if c.stringWidth(test_line, "Courier", 9) < width - 100:
                line = test_line
            else:
                c.drawString(60, y, line)
                y -= 11
                line = word
        if line:
            c.drawString(60, y, line)
            y -= 20

    # Signatures
    if y < 180:
        c.setFont("Courier", 8)
        c.drawString(50, 30, f"Page 2 of {data['total_pages']}")
        c.showPage()
        y = height - 60

    y -= 20
    c.setFont("Courier-Bold", 11)
    c.drawString(50, y, "AGREEMENT DATE:")
    y -= 18
    c.setFont("Courier", 10)
    c.drawString(70, y, data['agreement_date'])

    y -= 35
    c.setFont("Courier-Bold", 10)
    c.drawString(50, y, "SIGNATURES:")

    y -= 30
    c.setFont("Courier", 10)
    c.drawString(50, y, "Landlord: ______________________________")
    c.drawString(350, y, "Date: __________")

    y -= 30
    c.drawString(50, y, "Tenant: ________________________________")
    c.drawString(350, y, "Date: __________")

    y -= 30
    c.drawString(50, y, "Witness: _______________________________")
    c.drawString(350, y, "Date: __________")

    page_num = 3 if data['total_pages'] == 3 else 2
    c.setFont("Courier", 8)
    c.drawString(50, 30, f"Page {page_num} of {data['total_pages']}")

    c.save()

def generate_tenancy_data(prop, tenants, landlord, start_date, agency=None, is_joint=False, has_guarantor=False, has_break=False):
    """Generate complete tenancy agreement data"""

    term_months = random.choice([6, 6, 12, 12, 12, 12, 12])  # 70% 12-month
    end_date = start_date + timedelta(days=30 * term_months)
    agreement_date = start_date - timedelta(days=random.randint(7, 21))

    # Get tenant names
    if is_joint and len(tenants) >= 2:
        tenant_names = f"{tenants[0]['name']} and {tenants[1]['name']}"
        tenant_email = tenants[0]['email']
        tenant_phone = tenants[0].get('phone', '')
    else:
        tenant_names = tenants[0]['name']
        tenant_email = tenants[0]['email']
        tenant_phone = tenants[0].get('phone', '')

    # Calculate deposit (typically 5 weeks rent)
    monthly_rent = prop['monthly_rent']
    deposit = (monthly_rent * 12 / 52) * 5
    deposit = round(deposit / 10) * 10  # Round to nearest £10

    # Generate reference
    year = start_date.year
    seq = random.randint(10, 999)
    if agency:
        reference = generate_reference_number(agency['name'], year, seq)
    else:
        reference = f"AST/{year}/{seq:03d}"

    # Build terms
    terms = list(get_standard_terms())

    if has_break:
        terms.insert(7, add_break_clause())

    if has_guarantor:
        guarantor_name = random.choice(["Mr John Smith", "Mrs Sarah Johnson", "Dr Michael Brown", "Ms Emma Wilson"])
        terms.insert(4, add_guarantor_clause(guarantor_name))

    # Some include "How to Rent" acknowledgement
    if random.random() < 0.4:
        terms.append(("Government Publications", "The Tenant acknowledges receipt of the current version of the 'How to Rent: the checklist for renting in England' guide published by the Ministry of Housing, Communities and Local Government."))

    data = {
        'landlord_name': landlord['name'],
        'landlord_address': landlord['address'],
        'tenant_names': tenant_names,
        'tenant_email': tenant_email,
        'tenant_phone': tenant_phone,
        'property_address': prop['address'],
        'property_type': prop['type'],
        'furnished': prop['furnished'],
        'start_date': start_date.strftime('%d %B %Y'),
        'end_date': end_date.strftime('%d %B %Y'),
        'term_months': term_months,
        'monthly_rent': monthly_rent,
        'deposit': deposit,
        'deposit_scheme': random.choice(['Tenancy Deposit Scheme (TDS)', 'Deposit Protection Service (DPS)', 'MyDeposits']),
        'rent_day': random.choice(['1st', '15th', '28th']),
        'payment_method': random.choice(['Standing Order', 'Bank Transfer', 'Direct Debit']),
        'agreement_date': agreement_date.strftime('%d %B %Y'),
        'reference': reference,
        'terms': terms,
        'total_pages': 3 if len(terms) > 9 else 2
    }

    if agency:
        data['agency'] = agency['name']
        data['agency_address'] = agency['address']

    return data

# Main generation
print("Generating 35 Tenancy Agreement PDFs...")
print("=" * 60)

index_data = []
doc_count = 0

# Prepare tenancy scenarios
# We'll create 2-3 agreements per property with different dates/tenants

tenancy_configs = []

# For each property, create 2-3 tenancies
for idx, prop in enumerate(properties):
    num_tenancies = 2 if idx < 10 else (3 if idx < 5 else 2)

    for t_idx in range(num_tenancies):
        # Date ranges: older tenancies first
        if t_idx == 0:
            start_year = 2022
            start_month = random.randint(1, 12)
        elif t_idx == 1:
            start_year = random.choice([2023, 2024])
            start_month = random.randint(1, 12)
        else:
            start_year = random.choice([2024, 2025])
            start_month = random.randint(1, 12)

        start_date = datetime(start_year, start_month, random.choice([1, 15, 28]))

        # Select tenant(s)
        is_joint = random.random() < 0.3
        tenant_pool = random.sample(people, 2 if is_joint else 1)

        # Select agency or direct
        agency = None
        if random.random() < 0.4:
            agency = random.choice(agencies)

        # Other features
        has_guarantor = random.random() < 0.2
        has_break = random.random() < 0.15

        # Style distribution
        style_rand = random.random()
        if style_rand < 0.29:
            style = 'agency_branded'
        elif style_rand < 0.52:
            style = 'traditional'
        elif style_rand < 0.81:
            style = 'modern'
        else:
            style = 'basic'

        tenancy_configs.append({
            'property': prop,
            'tenants': tenant_pool,
            'landlord': random.choice([p for p in people if p.get('is_landlord', False)]),
            'start_date': start_date,
            'agency': agency,
            'is_joint': is_joint,
            'has_guarantor': has_guarantor,
            'has_break': has_break,
            'style': style
        })

# Limit to 35
tenancy_configs = tenancy_configs[:35]

# Generate PDFs
for idx, config in enumerate(tenancy_configs, 1):
    prop = config['property']
    data = generate_tenancy_data(
        prop,
        config['tenants'],
        config['landlord'],
        config['start_date'],
        config['agency'],
        config['is_joint'],
        config['has_guarantor'],
        config['has_break']
    )

    # Create short property identifier
    prop_short = prop['address'].split(',')[0].replace(' ', '_').replace("'", "")[:20]

    filename = f"test_documents/{idx:03d}_tenancy_{prop_short}.pdf"

    # Generate based on style
    if config['style'] == 'agency_branded':
        create_agency_branded_ast(filename, data)
    elif config['style'] == 'traditional':
        create_traditional_legal_ast(filename, data)
    elif config['style'] == 'modern':
        create_simple_modern_ast(filename, data)
    else:
        create_basic_landlord_ast(filename, data)

    # Add to index
    index_data.append({
        'filename': os.path.basename(filename),
        'document_type': 'Tenancy Agreement',
        'property_address': prop['address'],
        'primary_person': data['tenant_names'],
        'date': data['agreement_date']
    })

    doc_count += 1

    if doc_count % 5 == 0:
        print(f"Generated {doc_count}/35 tenancy agreements...")

# Write to index
index_file = 'test_documents/index.csv'
file_exists = os.path.isfile(index_file)

with open(index_file, 'a', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['filename', 'document_type', 'property_address', 'primary_person', 'date'])
    if not file_exists:
        writer.writeheader()
    writer.writerows(index_data)

print("=" * 60)
print(f"✓ Successfully generated {doc_count} tenancy agreement PDFs")
print(f"✓ Index updated: {index_file}")
print(f"✓ Files saved to: test_documents/")
