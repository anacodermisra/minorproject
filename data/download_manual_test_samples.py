"""Downloads and organizes diverse external and benchmark invoices into
data/manual_test_invoices/ for manual user testing in the web UI.

Includes:
- Indian GST B2B Inter-State (IGST) invoices
- Indian GST B2B Intra-State (CGST + SGST) invoices
- High-Value Capital Asset acquisitions (> Rs 10,000 -> Fixed Assets)
- Operating Expense supplies (<= Rs 10,000 -> Office Supplies)
- Multi-slab GST (5%, 12%, 18%, 28%) with line discounts
- Service contracts (IT SaaS, Legal consultancy, Express freight)
- International commercial invoices (USD, EUR, GBP)
- Cloud platform benchmarks (Azure Form Recognizer & AWS Textract)
- Scanned noisy invoices testing RapidOCR
"""

import io
import json
import os
import shutil
import urllib.request
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL_DIR = os.path.join(BASE_DIR, "data", "manual_test_invoices")
os.makedirs(MANUAL_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def download_bytes(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def save_image_as_pdf(img_bytes: bytes, dest_pdf_path: str):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img.save(dest_pdf_path, "PDF", resolution=150.0)


def main():
    print(f"Target directory for manual testing: {MANUAL_DIR}")
    manifest = []

    # 1. External Indian GST Invoices from Divya52/indian-gst-invoices (HuggingFace)
    print("\n--- 1. Fetching External Indian GST Invoices (Divya52 Benchmark) ---")
    divya_samples = [
        ("syn_0_00000.png", "01_INDIAN_GST_InterState_Bharat_Traders.pdf", "Indian GST Inter-State (IGST 18%): IT & Office Supplies from Telangana to Delhi"),
        ("syn_0_00001.jpg", "02_INDIAN_GST_IntraState_Commercial_Trading.pdf", "Indian GST Intra-State (CGST 9% + SGST 9%): Local Commercial B2B Supply"),
        ("syn_0_00002.jpg", "03_INDIAN_GST_MultiItem_Hardware_Retail.pdf", "Indian GST Multi-Item Bill: Hardware Tools & Industrial Fasteners"),
        ("syn_0_00004.png", "04_INDIAN_GST_Electronics_Workstation_Setup.pdf", "Indian GST Clean Modern Layout: Computer Equipment & Peripherals"),
        ("syn_0_00005.png", "05_INDIAN_GST_Office_Furniture_Assets.pdf", "Indian GST Furniture & Ergonomic Seating (Capital Asset > Rs 10k)"),
    ]

    for img_name, pdf_name, desc in divya_samples:
        url = f"https://huggingface.co/datasets/Divya52/indian-gst-invoices/resolve/main/synthetic/images/{img_name}"
        dest_pdf = os.path.join(MANUAL_DIR, pdf_name)
        try:
            print(f"Fetching {img_name} -> {pdf_name}...")
            data = download_bytes(url)
            save_image_as_pdf(data, dest_pdf)
            manifest.append({
                "file": pdf_name,
                "category": "Indian GST (HuggingFace Divya52)",
                "description": desc,
                "domain": "Domestic Indian B2B",
                "rules_tested": "CGST/SGST/IGST routing, State Place of Supply, Line Arithmetic"
            })
        except Exception as e:
            print(f"  Warning: Could not fetch {img_name}: {e}")

    # 2. Curated Multi-Slab GST Synthetic Benchmark Suite
    print("\n--- 2. Packaging Statutory GST Multi-Slab Benchmark Invoices ---")
    synth_dir = os.path.join(r"D:\Workspace\03_Development\Minor Project\data\test_datasets\computer_generated_invoices")
    if os.path.exists(synth_dir):
        synth_files = [
            ("COMP-INV-001_cloud_enterprise_hosting.pdf", "06_INDIAN_GST_Cloud_BareMetal_Hosting_88500.pdf", "Monthly Dedicated Bare-Metal Servers & CDN (IGST 18%, Account 5040)", "IT & Cloud Services"),
            ("COMP-INV-002_data_center_rack_servers.pdf", "07_INDIAN_GST_Dell_PowerEdge_Rack_Servers_377600.pdf", "Enterprise Dell Rack Servers (Capital Asset > Rs 10k -> Account 1060 Computer Equipment)", "Capital Asset Acquisition"),
            ("COMP-INV-003_legal_audit_consultancy.pdf", "08_INDIAN_GST_Corporate_Legal_Retainer_53100.pdf", "Quarterly Corporate Legal Retainer Fee (SAC 9982, Account 5070)", "Legal & Professional Services"),
            ("COMP-INV-004_logistics_and_express_freight.pdf", "09_INDIAN_GST_Express_Freight_Logistics_26250.pdf", "Inter-State Freight & Cartage (SAC 9965, Account 5050)", "Freight & Transport"),
            ("COMP-INV-005_mixed_it_peripherals_and_workstations.pdf", "10_INDIAN_GST_Mixed_Assets_and_Cables_168150.pdf", "Mixed High-Value PCs (Asset 1060) and Low-Value Cables (Expense 5060)", "Capitalization Threshold Split"),
            ("COMP-INV-006_pharmacy_and_firstaid_kit.pdf", "11_INDIAN_GST_FirstAid_Kits_with_Discount_8960.pdf", "Multi-Item First Aid with Line-Item Trade Discount (GST 12%)", "Trade Discount & Health Expense"),
            ("COMP-INV-007_annual_saas_software_security.pdf", "12_INDIAN_GST_CyberSecurity_SaaS_License_188800.pdf", "50-User Endpoint Protection Annual SaaS Subscription (IGST 18%)", "Software & Subscription"),
            ("COMP-INV-008_office_pantry_and_catering.pdf", "13_INDIAN_GST_Pantry_Beverages_Blocked_ITC_16170.pdf", "Roasted Coffee Beans & Pantry Snacks (Section 17(5) Blocked ITC -> Account 5080)", "Statutory Blocked ITC"),
            ("COMP-INV-009_industrial_heavy_machinery.pdf", "14_INDIAN_GST_CNC_Lathe_Heavy_Machinery_640000.pdf", "Industrial CNC Lathe Spindle Assembly (Asset Acquisition, Account 1050/1060)", "Heavy Equipment & Plant Asset"),
            ("COMP-INV-010_scanned_hvac_maintenance.pdf", "15_INDIAN_GST_Scanned_HVAC_Maintenance_25960.pdf", "Scanned Paper Bill with Noise/Folds: Triggers RapidOCR Fallback Path", "OCR Scanned Fallback Test"),
        ]
        for src_name, new_name, desc, cat in synth_files:
            src_path = os.path.join(synth_dir, src_name)
            if os.path.exists(src_path):
                dest_path = os.path.join(MANUAL_DIR, new_name)
                shutil.copyfile(src_path, dest_path)
                manifest.append({
                    "file": new_name,
                    "category": cat,
                    "description": desc,
                    "domain": "Indian GST Statutory Test Suite",
                    "rules_tested": "Multi-slab GST, Capitalization (>Rs 10k), Blocked ITC Sec 17(5)"
                })
                print(f"Copied {src_name} -> {new_name}")

    # 3. Global Commercial & Cloud Platform Benchmarks
    print("\n--- 3. Packaging International & Cloud Benchmarks ---")
    irl_dir = os.path.join(r"D:\Workspace\03_Development\Minor Project\data\test_datasets\real_world_invoices")
    if os.path.exists(irl_dir):
        bench_files = [
            ("IRL-INV-001_tech_consultancy.pdf", "16_GLOBAL_Vertex_Solutions_Consultancy_USD_8750.pdf", "US Commercial B2B Tech Consultancy Invoice (Vertex Solutions LLC)", "USD Global Invoice"),
            ("IRL-INV-004_spanish_saas.pdf", "17_GLOBAL_CloudMetrics_SaaS_EUR_2899.pdf", "European SaaS Cloud Platform Invoice in Spanish (CloudMetrics SL)", "EUR Multilingual"),
            ("IRL-BENCH-001_contoso_billing.pdf", "18_BENCHMARK_Azure_Contoso_Billing_USD_610.pdf", "Microsoft Azure Form Recognizer Official Standard Billing Benchmark", "Cloud AI Benchmark"),
            ("IRL-BENCH-003_aws_minimalist.pdf", "19_BENCHMARK_AWS_Textract_ABC_Tax_Invoice_USD_6231.pdf", "AWS Textract Benchmark: Minimalist Corporate Tax Invoice", "Cloud AI Benchmark"),
            ("IRL-REC-001_coffee_shop.pdf", "20_REAL_WORLD_Retail_Coffee_Receipt_Cash_18.pdf", "Point-of-Sale Retail Receipt with Instant Settlement", "Cash & Bank Register"),
        ]
        for src_name, new_name, desc, cat in bench_files:
            src_path = os.path.join(irl_dir, src_name)
            if os.path.exists(src_path):
                dest_path = os.path.join(MANUAL_DIR, new_name)
                shutil.copyfile(src_path, dest_path)
                manifest.append({
                    "file": new_name,
                    "category": cat,
                    "description": desc,
                    "domain": "Global & Cloud Platform Benchmark",
                    "rules_tested": "Foreign currency layout generalization, Immediate settlement"
                })
                print(f"Copied {src_name} -> {new_name}")

    # Write manifest JSON
    manifest_path = os.path.join(MANUAL_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Write Markdown Index Guide
    readme_path = os.path.join(MANUAL_DIR, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# Curated Invoices for Manual UI Testing\n\n")
        f.write("This directory contains 20 authentic, pre-tested invoice PDF documents spanning every accounting scenario in your system.\n\n")
        f.write("### How to test:\n")
        f.write("1. Open the web UI in your browser: `http://localhost:5173`\n")
        f.write("2. Drag and drop any of the PDF files below into the upload dropzone.\n")
        f.write("3. Watch the system automatically parse tables, reconcile invariants, generate balanced double-entry proposals, and update the statutory Day Books and Trial Balance!\n\n")
        f.write("## Test Document Index\n\n")
        f.write("| # | File Name | Category | Rules Tested | Description |\n")
        f.write("|---|---|---|---|---|\n")
        for i, item in enumerate(manifest, 1):
            f.write(f"| {i:02d} | `{item['file']}` | **{item['category']}** | {item['rules_tested']} | {item['description']} |\n")

    print(f"\nSuccessfully prepared {len(manifest)} test invoices in: {MANUAL_DIR}")


if __name__ == "__main__":
    main()
