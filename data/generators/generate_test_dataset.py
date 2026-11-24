"""Generates a rich suite of realistic computer-generated (synthetic) invoices.

Includes:
- Multi-slab GST (5%, 12%, 18%, 28%)
- Intra-state (CGST + SGST) and Inter-state (IGST)
- Capital Asset purchases vs Operating Expenses
- Line-item discounts and lump-sum discounts
- Rasterized scanned noisy copy for testing the RapidOCR path
- Full paired JSON ground-truth and metadata manifest
"""

import json
import os
import pymupdf
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST_DIR = os.path.join(BASE_DIR, "test_datasets", "computer_generated_invoices")
os.makedirs(DEST_DIR, exist_ok=True)


def build_pdf_invoice(filepath: str, data: dict, accent_color: str = "#1E3A8A"):
    """Generates an invoice PDF using ReportLab with custom styling."""
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []

    title_style = ParagraphStyle(
        name="TitleStyle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor(accent_color),
    )
    normal = ParagraphStyle(name="Normal", fontName="Helvetica", fontSize=9, leading=13)
    normal_bold = ParagraphStyle(name="Bold", fontName="Helvetica-Bold", fontSize=9, leading=13)

    # 1. Vendor Header
    story.append(Paragraph(data["vendor_name"], title_style))
    story.append(Paragraph(f"GSTIN: {data.get('vendor_gstin', 'N/A')}", normal))
    story.append(Paragraph(f"Address: {data.get('vendor_address', 'India')}", normal))
    story.append(Spacer(1, 14))

    # 2. Meta Info (Invoice #, Date, Buyer, Place of Supply)
    meta_data = [
        [
            Paragraph(f"<b>Invoice No:</b> {data['invoice_number']}", normal),
            Paragraph(f"<b>Billed To:</b> {data['buyer_name']}", normal),
        ],
        [
            Paragraph(f"<b>Invoice Date:</b> {data['invoice_date']}", normal),
            Paragraph(f"<b>Buyer GSTIN:</b> {data.get('buyer_gstin', 'N/A')}", normal),
        ],
        [
            Paragraph(f"<b>Due Date:</b> {data.get('due_date', 'N/A')}", normal),
            Paragraph(f"<b>Place of Supply:</b> {data.get('place_of_supply', 'Delhi (07)')}", normal),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 3. Line Items Table
    table_data = [["Item Description", "HSN/SAC", "Qty", "Unit Price", "Discount", "Total (INR)"]]
    for item in data["line_items"]:
        table_data.append([
            item["description"],
            item.get("hsn_sac", "-"),
            str(item["quantity"]),
            f"{float(item['unit_price']):,.2f}",
            f"{float(item.get('discount_amount', 0)):,.2f}",
            f"{float(item['total_amount']):,.2f}",
        ])

    items_table = Table(table_data, colWidths=[200, 70, 45, 80, 65, 80])
    items_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(items_table)
    story.append(Spacer(1, 14))

    # 4. Summary Totals Table
    totals_data = [
        ["Subtotal:", f"INR {float(data['subtotal']):,.2f}"],
        ["Total Tax (GST):", f"INR {float(data['total_tax']):,.2f}"],
    ]
    if float(data.get("total_discount", 0)) > 0:
        totals_data.append(["Total Discount:", f"INR {float(data['total_discount']):,.2f}"])
    totals_data.append(["Grand Total:", f"INR {float(data['grand_total']):,.2f}"])

    totals_table = Table(totals_data, colWidths=[420, 120])
    totals_table.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 10.5),
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor(accent_color)),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    story.append(totals_table)

    doc.build(story)


def make_scanned_copy(source: str, destination: str, dpi: int = 200) -> None:
    """Rasterizes a PDF into an image-only PDF with no text layer (exercises RapidOCR)."""
    original = pymupdf.open(source)
    output = pymupdf.open()
    for page in original:
        pixmap = page.get_pixmap(dpi=dpi)
        image_page = output.new_page(width=page.rect.width, height=page.rect.height)
        image_page.insert_image(image_page.rect, pixmap=pixmap)
    output.save(destination)
    original.close()
    output.close()


def generate_all_invoices():
    dataset_records = [
        # 1. Cloud Infrastructure (Inter-State IGST 18%)
        {
            "id": "COMP-INV-001_cloud_enterprise_hosting",
            "accent": "#0284C7",
            "category": "Technology & Hosting (Operating Expense)",
            "scenario": "Inter-state supply (Karnataka to Delhi), 18% IGST operating software expense.",
            "data": {
                "invoice_number": "INV-COMP-001",
                "invoice_date": "2026-11-01",
                "due_date": "2026-11-20",
                "vendor_name": "Apex Cloud Infrastructure Technologies",
                "vendor_gstin": "29AAACA1234D1Z2",
                "vendor_address": "Electronic City, Bengaluru, Karnataka - 560100",
                "buyer_name": "Modern Tech Solutions Pvt Ltd",
                "buyer_gstin": "07BBBBB1111B1Z2",
                "place_of_supply": "Delhi (07)",
                "subtotal": 75000.00,
                "total_discount": 0.00,
                "total_tax": 13500.00,
                "grand_total": 88500.00,
                "line_items": [
                    {"description": "Dedicated Bare-Metal Node (Monthly)", "hsn_sac": "998315", "quantity": 1, "unit_price": 50000.00, "discount_amount": 0.00, "tax_rate_percent": 18.0, "total_amount": 50000.00},
                    {"description": "Global CDN Bandwidth & Edge Caching", "hsn_sac": "998315", "quantity": 1, "unit_price": 25000.00, "discount_amount": 0.00, "tax_rate_percent": 18.0, "total_amount": 25000.00},
                ],
                "taxes": [{"tax_type": "IGST", "rate_percent": 18.0, "taxable_amount": 75000.00, "tax_amount": 13500.00}],
                "accounting_ground_truth": {
                    "transaction_type": "EXPENSE_OPERATING",
                    "journal_lines": [
                        {"account_code": "5020", "account_name": "Server & Hosting Expense A/c", "entry_type": "DEBIT", "amount": 75000.00},
                        {"account_code": "1083", "account_name": "Input IGST A/c", "entry_type": "DEBIT", "amount": 13500.00},
                        {"account_code": "2010", "account_name": "Apex Cloud Technologies (Creditor)", "entry_type": "CREDIT", "amount": 88500.00},
                    ]
                }
            }
        },

        # 2. Data Center Servers (Asset Capitalization Rule > 10,000 INR)
        {
            "id": "COMP-INV-002_data_center_rack_servers",
            "accent": "#1E3A8A",
            "category": "Capital Equipment (Asset Purchase)",
            "scenario": "High-value servers (> 10,000 threshold), capitalized to Fixed Assets with 18% IGST.",
            "data": {
                "invoice_number": "INV-COMP-002",
                "invoice_date": "2026-11-03",
                "due_date": "2026-12-03",
                "vendor_name": "Silicon Rack Solutions India",
                "vendor_gstin": "09AACCS4455H1ZK",
                "vendor_address": "Sector 63, Noida, Uttar Pradesh - 201301",
                "buyer_name": "Modern Tech Solutions Pvt Ltd",
                "buyer_gstin": "07BBBBB1111B1Z2",
                "place_of_supply": "Delhi (07)",
                "subtotal": 320000.00,
                "total_discount": 0.00,
                "total_tax": 57600.00,
                "grand_total": 377600.00,
                "line_items": [
                    {"description": "Enterprise 2U Rack Server (64-Core Xeon)", "hsn_sac": "8471", "quantity": 2, "unit_price": 160000.00, "discount_amount": 0.00, "tax_rate_percent": 18.0, "total_amount": 320000.00},
                ],
                "taxes": [{"tax_type": "IGST", "rate_percent": 18.0, "taxable_amount": 320000.00, "tax_amount": 57600.00}],
                "accounting_ground_truth": {
                    "transaction_type": "ASSET_ACQUISITION",
                    "journal_lines": [
                        {"account_code": "1040", "account_name": "Computer Equipment & Hardware (Asset)", "entry_type": "DEBIT", "amount": 320000.00},
                        {"account_code": "1083", "account_name": "Input IGST A/c", "entry_type": "DEBIT", "amount": 57600.00},
                        {"account_code": "2010", "account_name": "Silicon Rack Solutions (Creditor)", "entry_type": "CREDIT", "amount": 377600.00},
                    ]
                }
            }
        },

        # 3. Corporate Legal & Compliance Advisory (Intra-State CGST+SGST 18%)
        {
            "id": "COMP-INV-003_legal_audit_consultancy",
            "accent": "#4338CA",
            "category": "Professional Fees (Operating Expense)",
            "scenario": "Intra-state legal advisory (Delhi to Delhi), 9% CGST + 9% SGST.",
            "data": {
                "invoice_number": "INV-COMP-003",
                "invoice_date": "2026-11-05",
                "due_date": "2026-11-25",
                "vendor_name": "Singhania & Partners LLP",
                "vendor_gstin": "07AAAFS9988R1ZX",
                "vendor_address": "Barakhamba Road, Connaught Place, New Delhi - 110001",
                "buyer_name": "Modern Tech Solutions Pvt Ltd",
                "buyer_gstin": "07BBBBB1111B1Z2",
                "place_of_supply": "Delhi (07)",
                "subtotal": 45000.00,
                "total_discount": 0.00,
                "total_tax": 8100.00,
                "grand_total": 53100.00,
                "line_items": [
                    {"description": "Quarterly Corporate Legal Compliance Retainer", "hsn_sac": "998211", "quantity": 1, "unit_price": 45000.00, "discount_amount": 0.00, "tax_rate_percent": 18.0, "total_amount": 45000.00},
                ],
                "taxes": [
                    {"tax_type": "CGST", "rate_percent": 9.0, "taxable_amount": 45000.00, "tax_amount": 4050.00},
                    {"tax_type": "SGST", "rate_percent": 9.0, "taxable_amount": 45000.00, "tax_amount": 4050.00},
                ],
                "accounting_ground_truth": {
                    "transaction_type": "EXPENSE_PROFESSIONAL",
                    "journal_lines": [
                        {"account_code": "5030", "account_name": "Legal & Professional Fees A/c", "entry_type": "DEBIT", "amount": 45000.00},
                        {"account_code": "1081", "account_name": "Input CGST A/c", "entry_type": "DEBIT", "amount": 4050.00},
                        {"account_code": "1082", "account_name": "Input SGST A/c", "entry_type": "DEBIT", "amount": 4050.00},
                        {"account_code": "2010", "account_name": "Singhania & Partners (Creditor)", "entry_type": "CREDIT", "amount": 53100.00},
                    ]
                }
            }
        },

        # 4. Logistics Freight Forwarding (5% GST slab with Discount)
        {
            "id": "COMP-INV-004_logistics_and_express_freight",
            "accent": "#D97706",
            "category": "Freight & Shipping (Discounted Supply)",
            "scenario": "Transportation service with 5% GST rate and trade discount applied.",
            "data": {
                "invoice_number": "INV-COMP-004",
                "invoice_date": "2026-11-07",
                "due_date": "2026-11-21",
                "vendor_name": "SpeedCargo Logistics India",
                "vendor_gstin": "06AABCS7788J1ZZ",
                "vendor_address": "Cyber City, Gurugram, Haryana - 122002",
                "buyer_name": "Modern Tech Solutions Pvt Ltd",
                "buyer_gstin": "07BBBBB1111B1Z2",
                "place_of_supply": "Delhi (07)",
                "subtotal": 28000.00,
                "total_discount": 3000.00,
                "total_tax": 1250.00,
                "grand_total": 26250.00,
                "line_items": [
                    {"description": "Inter-city Equipment Transport & Drayage", "hsn_sac": "996511", "quantity": 1, "unit_price": 28000.00, "discount_amount": 3000.00, "tax_rate_percent": 5.0, "total_amount": 25000.00},
                ],
                "taxes": [{"tax_type": "IGST", "rate_percent": 5.0, "taxable_amount": 25000.00, "tax_amount": 1250.00}],
                "accounting_ground_truth": {
                    "transaction_type": "EXPENSE_FREIGHT",
                    "journal_lines": [
                        {"account_code": "5040", "account_name": "Freight & Shipping Expense A/c", "entry_type": "DEBIT", "amount": 25000.00},
                        {"account_code": "1083", "account_name": "Input IGST A/c", "entry_type": "DEBIT", "amount": 1250.00},
                        {"account_code": "2010", "account_name": "SpeedCargo Logistics (Creditor)", "entry_type": "CREDIT", "amount": 26250.00},
                    ]
                }
            }
        },

        # 5. Mixed IT Equipment & Consumables (Asset vs Expense Split)
        {
            "id": "COMP-INV-005_mixed_it_peripherals_and_workstations",
            "accent": "#059669",
            "category": "Mixed Asset & Expense Invoice",
            "scenario": "Invoice with both capital assets (> 10k) and operating consumables (<= 10k).",
            "data": {
                "invoice_number": "INV-COMP-005",
                "invoice_date": "2026-11-09",
                "due_date": "2026-12-09",
                "vendor_name": "Dynatech Digital Hub Private Limited",
                "vendor_gstin": "07AACCD8877K1Z4",
                "vendor_address": "Nehru Place, New Delhi - 110019",
                "buyer_name": "Modern Tech Solutions Pvt Ltd",
                "buyer_gstin": "07BBBBB1111B1Z2",
                "place_of_supply": "Delhi (07)",
                "subtotal": 142500.00,
                "total_discount": 0.00,
                "total_tax": 25650.00,
                "grand_total": 168150.00,
                "line_items": [
                    {"description": "Core-i9 Developer Workstation PC", "hsn_sac": "8471", "quantity": 1, "unit_price": 125000.00, "discount_amount": 0.00, "tax_rate_percent": 18.0, "total_amount": 125000.00},
                    {"description": "USB-C Dual 4K Docking Stations", "hsn_sac": "8471", "quantity": 2, "unit_price": 7500.00, "discount_amount": 0.00, "tax_rate_percent": 18.0, "total_amount": 15000.00},
                    {"description": "Cat-6 High-Speed Ethernet Cables (Pack of 5)", "hsn_sac": "8544", "quantity": 5, "unit_price": 500.00, "discount_amount": 0.00, "tax_rate_percent": 18.0, "total_amount": 2500.00},
                ],
                "taxes": [
                    {"tax_type": "CGST", "rate_percent": 9.0, "taxable_amount": 142500.00, "tax_amount": 12825.00},
                    {"tax_type": "SGST", "rate_percent": 9.0, "taxable_amount": 142500.00, "tax_amount": 12825.00},
                ],
                "accounting_ground_truth": {
                    "transaction_type": "MIXED_ASSET_EXPENSE",
                    "journal_lines": [
                        {"account_code": "1040", "account_name": "Computer Hardware (Capitalized Asset)", "entry_type": "DEBIT", "amount": 125000.00},
                        {"account_code": "5010", "account_name": "Office & IT Supplies (Expensed)", "entry_type": "DEBIT", "amount": 17500.00},
                        {"account_code": "1081", "account_name": "Input CGST A/c", "entry_type": "DEBIT", "amount": 12825.00},
                        {"account_code": "1082", "account_name": "Input SGST A/c", "entry_type": "DEBIT", "amount": 12825.00},
                        {"account_code": "2010", "account_name": "Dynatech Digital Hub (Creditor)", "entry_type": "CREDIT", "amount": 168150.00},
                    ]
                }
            }
        },

        # 6. Corporate Pharmacy & First-Aid Supplies (12% GST Slab)
        {
            "id": "COMP-INV-006_pharmacy_and_firstaid_kit",
            "accent": "#E11D48",
            "category": "Health & Safety Consumables (12% GST)",
            "scenario": "Staff first-aid and medical supplies categorized under 12% GST slab.",
            "data": {
                "invoice_number": "INV-COMP-006",
                "invoice_date": "2026-11-10",
                "due_date": "2026-11-20",
                "vendor_name": "MediCare Supplies India",
                "vendor_gstin": "07AAACM3322E1Z1",
                "vendor_address": "Lajpat Nagar, New Delhi - 110024",
                "buyer_name": "Modern Tech Solutions Pvt Ltd",
                "buyer_gstin": "07BBBBB1111B1Z2",
                "place_of_supply": "Delhi (07)",
                "subtotal": 8500.00,
                "total_discount": 500.00,
                "total_tax": 960.00,
                "grand_total": 8960.00,
                "line_items": [
                    {"description": "Commercial First-Aid Wall Mounted Kits", "hsn_sac": "3005", "quantity": 4, "unit_price": 1500.00, "discount_amount": 500.00, "tax_rate_percent": 12.0, "total_amount": 5500.00},
                    {"description": "Digital Blood Pressure & Health Monitors", "hsn_sac": "9018", "quantity": 1, "unit_price": 2500.00, "discount_amount": 0.00, "tax_rate_percent": 12.0, "total_amount": 2500.00},
                ],
                "taxes": [
                    {"tax_type": "CGST", "rate_percent": 6.0, "taxable_amount": 8000.00, "tax_amount": 480.00},
                    {"tax_type": "SGST", "rate_percent": 6.0, "taxable_amount": 8000.00, "tax_amount": 480.00},
                ],
                "accounting_ground_truth": {
                    "transaction_type": "EXPENSE_WELFARE",
                    "journal_lines": [
                        {"account_code": "5050", "account_name": "Staff Welfare & Medical Expense", "entry_type": "DEBIT", "amount": 8000.00},
                        {"account_code": "1081", "account_name": "Input CGST A/c", "entry_type": "DEBIT", "amount": 480.00},
                        {"account_code": "1082", "account_name": "Input SGST A/c", "entry_type": "DEBIT", "amount": 480.00},
                        {"account_code": "2010", "account_name": "MediCare Supplies India (Creditor)", "entry_type": "CREDIT", "amount": 8960.00},
                    ]
                }
            }
        },

        # 7. Annual SaaS Security Subscription (High Value Operating Expense)
        {
            "id": "COMP-INV-007_annual_saas_software_security",
            "accent": "#7C3AED",
            "category": "Software Subscriptions (Prepaid / Expense)",
            "scenario": "Annual cybersecurity software license, 18% IGST with volume partner discount.",
            "data": {
                "invoice_number": "INV-COMP-007",
                "invoice_date": "2026-11-12",
                "due_date": "2026-12-12",
                "vendor_name": "CyberShield Security Systems Pvt Ltd",
                "vendor_gstin": "27AAACC8899K1Z5",
                "vendor_address": "BKC, Mumbai, Maharashtra - 400051",
                "buyer_name": "Modern Tech Solutions Pvt Ltd",
                "buyer_gstin": "07BBBBB1111B1Z2",
                "place_of_supply": "Delhi (07)",
                "subtotal": 180000.00,
                "total_discount": 20000.00,
                "total_tax": 28800.00,
                "grand_total": 188800.00,
                "line_items": [
                    {"description": "Enterprise Endpoint Detection & Response (100 seats)", "hsn_sac": "998313", "quantity": 1, "unit_price": 180000.00, "discount_amount": 20000.00, "tax_rate_percent": 18.0, "total_amount": 160000.00},
                ],
                "taxes": [{"tax_type": "IGST", "rate_percent": 18.0, "taxable_amount": 160000.00, "tax_amount": 28800.00}],
                "accounting_ground_truth": {
                    "transaction_type": "EXPENSE_SOFTWARE",
                    "journal_lines": [
                        {"account_code": "5020", "account_name": "Software & Security Licenses A/c", "entry_type": "DEBIT", "amount": 160000.00},
                        {"account_code": "1083", "account_name": "Input IGST A/c", "entry_type": "DEBIT", "amount": 28800.00},
                        {"account_code": "2010", "account_name": "CyberShield Security (Creditor)", "entry_type": "CREDIT", "amount": 188800.00},
                    ]
                }
            }
        },

        # 8. Office Pantry & Catering Services (5% Slab)
        {
            "id": "COMP-INV-008_office_pantry_and_catering",
            "accent": "#EA580C",
            "category": "Pantry & Refreshments (5% GST)",
            "scenario": "Monthly office beverages and pantry refreshments at 5% GST.",
            "data": {
                "invoice_number": "INV-COMP-008",
                "invoice_date": "2026-11-14",
                "due_date": "2026-11-28",
                "vendor_name": "Royal Hospitality & Pantry Services",
                "vendor_gstin": "07AAACR1199F1Z0",
                "vendor_address": "Saket District Centre, New Delhi - 110017",
                "buyer_name": "Modern Tech Solutions Pvt Ltd",
                "buyer_gstin": "07BBBBB1111B1Z2",
                "place_of_supply": "Delhi (07)",
                "subtotal": 15400.00,
                "total_discount": 0.00,
                "total_tax": 770.00,
                "grand_total": 16170.00,
                "line_items": [
                    {"description": "Bean-to-Cup Coffee Beans & Fresh Milk Packets", "hsn_sac": "2101", "quantity": 1, "unit_price": 9400.00, "discount_amount": 0.00, "tax_rate_percent": 5.0, "total_amount": 9400.00},
                    {"description": "Assorted Healthy Snacks & Green Tea Cartons", "hsn_sac": "0902", "quantity": 1, "unit_price": 6000.00, "discount_amount": 0.00, "tax_rate_percent": 5.0, "total_amount": 6000.00},
                ],
                "taxes": [
                    {"tax_type": "CGST", "rate_percent": 2.5, "taxable_amount": 15400.00, "tax_amount": 385.00},
                    {"tax_type": "SGST", "rate_percent": 2.5, "taxable_amount": 15400.00, "tax_amount": 385.00},
                ],
                "accounting_ground_truth": {
                    "transaction_type": "EXPENSE_PANTRY",
                    "journal_lines": [
                        {"account_code": "5060", "account_name": "Office Pantry & Refreshments A/c", "entry_type": "DEBIT", "amount": 15400.00},
                        {"account_code": "1081", "account_name": "Input CGST A/c", "entry_type": "DEBIT", "amount": 385.00},
                        {"account_code": "1082", "account_name": "Input SGST A/c", "entry_type": "DEBIT", "amount": 385.00},
                        {"account_code": "2010", "account_name": "Royal Hospitality (Creditor)", "entry_type": "CREDIT", "amount": 16170.00},
                    ]
                }
            }
        },

        # 9. Heavy Industrial Capital Asset (28% GST Slab)
        {
            "id": "COMP-INV-009_industrial_heavy_machinery",
            "accent": "#475569",
            "category": "Heavy Capital Machinery (28% GST)",
            "scenario": "Commercial manufacturing / fabrication machinery subject to 28% IGST.",
            "data": {
                "invoice_number": "INV-COMP-009",
                "invoice_date": "2026-11-15",
                "due_date": "2026-12-15",
                "vendor_name": "Bharat Industrial Fabricators",
                "vendor_gstin": "06AAACB9900L1ZX",
                "vendor_address": "Industrial Area, Faridabad, Haryana - 121001",
                "buyer_name": "Modern Tech Solutions Pvt Ltd",
                "buyer_gstin": "07BBBBB1111B1Z2",
                "place_of_supply": "Delhi (07)",
                "subtotal": 500000.00,
                "total_discount": 0.00,
                "total_tax": 140000.00,
                "grand_total": 640000.00,
                "line_items": [
                    {"description": "Precision CNC Laser Cutting Machinery", "hsn_sac": "8456", "quantity": 1, "unit_price": 500000.00, "discount_amount": 0.00, "tax_rate_percent": 28.0, "total_amount": 500000.00},
                ],
                "taxes": [{"tax_type": "IGST", "rate_percent": 28.0, "taxable_amount": 500000.00, "tax_amount": 140000.00}],
                "accounting_ground_truth": {
                    "transaction_type": "ASSET_ACQUISITION",
                    "journal_lines": [
                        {"account_code": "1030", "account_name": "Plant & Heavy Machinery (Asset)", "entry_type": "DEBIT", "amount": 500000.00},
                        {"account_code": "1083", "account_name": "Input IGST A/c", "entry_type": "DEBIT", "amount": 140000.00},
                        {"account_code": "2010", "account_name": "Bharat Industrial Fabricators (Creditor)", "entry_type": "CREDIT", "amount": 640000.00},
                    ]
                }
            }
        },

        # 10. Scanned / Rasterized HVAC Maintenance Invoice (RapidOCR Path)
        {
            "id": "COMP-INV-010_scanned_hvac_maintenance",
            "accent": "#0D9488",
            "category": "Repairs & Maintenance (Scanned Document)",
            "scenario": "Simulated physical scan without digital text layer to exercise the RapidOCR fallback engine.",
            "is_scanned": True,
            "data": {
                "invoice_number": "INV-COMP-010",
                "invoice_date": "2026-11-16",
                "due_date": "2026-11-30",
                "vendor_name": "ClimateControl Engineering Services",
                "vendor_gstin": "07AAACC4433D1ZP",
                "vendor_address": "Okhla Industrial Area Phase-III, New Delhi - 110020",
                "buyer_name": "Modern Tech Solutions Pvt Ltd",
                "buyer_gstin": "07BBBBB1111B1Z2",
                "place_of_supply": "Delhi (07)",
                "subtotal": 22000.00,
                "total_discount": 0.00,
                "total_tax": 3960.00,
                "grand_total": 25960.00,
                "line_items": [
                    {"description": "Quarterly HVAC Central AC Maintenance & Filter Replacement", "hsn_sac": "998719", "quantity": 1, "unit_price": 22000.00, "discount_amount": 0.00, "tax_rate_percent": 18.0, "total_amount": 22000.00},
                ],
                "taxes": [
                    {"tax_type": "CGST", "rate_percent": 9.0, "taxable_amount": 22000.00, "tax_amount": 1980.00},
                    {"tax_type": "SGST", "rate_percent": 9.0, "taxable_amount": 22000.00, "tax_amount": 1980.00},
                ],
                "accounting_ground_truth": {
                    "transaction_type": "EXPENSE_MAINTENANCE",
                    "journal_lines": [
                        {"account_code": "5070", "account_name": "Repairs & Maintenance A/c", "entry_type": "DEBIT", "amount": 22000.00},
                        {"account_code": "1081", "account_name": "Input CGST A/c", "entry_type": "DEBIT", "amount": 1980.00},
                        {"account_code": "1082", "account_name": "Input SGST A/c", "entry_type": "DEBIT", "amount": 1980.00},
                        {"account_code": "2010", "account_name": "ClimateControl Engineering (Creditor)", "entry_type": "CREDIT", "amount": 25960.00},
                    ]
                }
            }
        },
    ]

    manifest = []

    for item in dataset_records:
        rec_id = item["id"]
        pdf_name = f"{rec_id}.pdf"
        json_name = f"{rec_id}.json"
        pdf_path = os.path.join(DEST_DIR, pdf_name)
        json_path = os.path.join(DEST_DIR, json_name)

        # Build clean PDF
        build_pdf_invoice(pdf_path, item["data"], item.get("accent", "#1E3A8A"))

        # If marked as scanned copy, rasterize it into an image-only PDF
        if item.get("is_scanned"):
            clean_temp = os.path.join(DEST_DIR, f"clean_{pdf_name}")
            os.rename(pdf_path, clean_temp)
            make_scanned_copy(clean_temp, pdf_path, dpi=200)
            if os.path.exists(clean_temp):
                os.remove(clean_temp)
            print(f"Generated scanned-looking copy (no text layer): {pdf_name}")
        else:
            print(f"Generated PDF: {pdf_name}")

        # Save paired ground-truth JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(item["data"], f, indent=2)

        manifest.append({
            "id": rec_id,
            "file": pdf_name,
            "ground_truth_file": json_name,
            "category": item["category"],
            "scenario": item["scenario"],
            "currency": "INR",
            "grand_total": item["data"]["grand_total"],
            "tax_structure": ", ".join(f"{t['tax_type']} {t['rate_percent']}%" for t in item["data"]["taxes"]),
            "is_scanned_ocr": item.get("is_scanned", False)
        })

    # Save manifest
    manifest_path = os.path.join(DEST_DIR, "dataset_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Save documentation README
    readme_path = os.path.join(DEST_DIR, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# Computer-Generated (Synthetic) Test Invoices\n\n")
        f.write("A benchmark suite of 10 computer-generated invoices covering all edge cases in GST calculation, asset capitalization thresholds, multi-rate tax brackets, discounts, and OCR fallback.\n\n")
        f.write("## Dataset Characteristics\n\n")
        f.write("- **Total Documents:** 10 comprehensive invoices\n")
        f.write("- **Tax Slabs Covered:** 5%, 12%, 18%, 28% GST, both Intra-State (CGST + SGST) and Inter-State (IGST)\n")
        f.write("- **Accounting Logic Covered:** Fixed Asset Capitalization (> ₹10k threshold), Consumables Expensing, Operating Software Subscriptions, Freight, Mixed Asset/Expense Split\n")
        f.write("- **OCR Fallback Coverage:** `COMP-INV-010` is an image-only scanned PDF to test the RapidOCR fallback pipeline\n")
        f.write("- **Ground Truth:** Every PDF has a paired `.json` file with full field-by-field and journal entry ground truth\n\n")
        f.write("## Inventory Table\n\n")
        f.write("| ID | File | Category | Total (INR) | Tax Structure | Extraction Engine |\n")
        f.write("|---|---|---|---|---|---|\n")
        for m in manifest:
            engine = "RapidOCR Fallback" if m["is_scanned_ocr"] else "PyMuPDF Fast Text Layer"
            f.write(f"| `{m['id']}` | [{m['file']}]({m['file']}) | {m['category']} | INR {m['grand_total']:,.2f} | {m['tax_structure']} | {engine} |\n")

    print(f"\nGenerated all 10 computer-generated invoices with ground-truth at: {DEST_DIR}")


if __name__ == "__main__":
    generate_all_invoices()
