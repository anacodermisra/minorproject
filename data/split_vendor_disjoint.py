"""Strict 60-40 Vendor-Disjoint Train/Test Dataset Splitting Protocol.

Implements vendor-level partitioning to guarantee zero data leakage between
training/calibration and evaluation benchmarks. Every vendor appears in either
the Train set or the Test set, never both:
    Vendors(Train) ∩ Vendors(Test) = ∅
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Reference to dataset directories (supporting both primary and secondary clones)
SYNTH_DIR = DATA_DIR / "test_datasets" / "computer_generated_invoices"
if not SYNTH_DIR.exists():
    SYNTH_DIR = Path(r"D:\Workspace\03_Development\Minor Project\data\test_datasets\computer_generated_invoices")

IRL_DIR = DATA_DIR / "test_datasets" / "real_world_invoices"
if not IRL_DIR.exists():
    IRL_DIR = Path(r"D:\Workspace\03_Development\Minor Project\data\test_datasets\real_world_invoices")


def build_split() -> Dict[str, Any]:
    # 1. Synthetic Indian GST Benchmark (10 Invoices, 10 Unique Vendors)
    # 60% Train (6 vendors) / 40% Test (4 vendors)
    synth_train_vendors = [
        "Apex Cloud Infrastructure Technologies",
        "Silicon Rack Solutions India",
        "Singhania & Partners LLP",
        "SpeedCargo Logistics India",
        "Dynatech Digital Hub Private Limited",
        "MediCare Supplies India",
    ]
    synth_test_vendors = [
        "CyberShield Security Systems Pvt Ltd",
        "Royal Hospitality & Pantry Services",
        "Bharat Industrial Fabricators",
        "ClimateControl Engineering Services",
    ]

    # Map invoices to synthetic vendors
    synth_invoices = [
        {
            "id": "COMP-INV-001",
            "pdf_file": "COMP-INV-001_cloud_enterprise_hosting.pdf",
            "json_file": "COMP-INV-001_cloud_enterprise_hosting.json",
            "vendor": "Apex Cloud Infrastructure Technologies",
            "domain": "IT & Cloud Hosting",
            "statutory_category": "Standard Rate (18% IGST)",
            "rules": ["Inter-State IGST", "Service Account 5040", "Exact Line Totals"]
        },
        {
            "id": "COMP-INV-002",
            "pdf_file": "COMP-INV-002_data_center_rack_servers.pdf",
            "json_file": "COMP-INV-002_data_center_rack_servers.json",
            "vendor": "Silicon Rack Solutions India",
            "domain": "Hardware Infrastructure",
            "statutory_category": "Capital Asset Acquisition (> ₹10,000)",
            "rules": ["Capitalization Threshold", "Account 1060 Computer Equipment", "Inter-State IGST"]
        },
        {
            "id": "COMP-INV-003",
            "pdf_file": "COMP-INV-003_legal_audit_consultancy.pdf",
            "json_file": "COMP-INV-003_legal_audit_consultancy.json",
            "vendor": "Singhania & Partners LLP",
            "domain": "Legal & Corporate Consultancy",
            "statutory_category": "Professional Services Retainer",
            "rules": ["SAC 9982", "Account 5070 Legal", "Intra-State CGST+SGST"]
        },
        {
            "id": "COMP-INV-004",
            "pdf_file": "COMP-INV-004_logistics_and_express_freight.pdf",
            "json_file": "COMP-INV-004_logistics_and_express_freight.json",
            "vendor": "SpeedCargo Logistics India",
            "domain": "Freight & Logistics",
            "statutory_category": "Transportation of Goods",
            "rules": ["SAC 9965", "Account 5050 Freight", "GST 5%"]
        },
        {
            "id": "COMP-INV-005",
            "pdf_file": "COMP-INV-005_mixed_it_peripherals_and_workstations.pdf",
            "json_file": "COMP-INV-005_mixed_it_peripherals_and_workstations.json",
            "vendor": "Dynatech Digital Hub Private Limited",
            "domain": "IT Equipment & Accessories",
            "statutory_category": "Mixed Asset & Expense Split",
            "rules": ["Capitalization Split (> ₹10,000 -> 1060, <= ₹10,000 -> 5060)", "CGST+SGST 18%"]
        },
        {
            "id": "COMP-INV-006",
            "pdf_file": "COMP-INV-006_pharmacy_and_firstaid_kit.pdf",
            "json_file": "COMP-INV-006_pharmacy_and_firstaid_kit.json",
            "vendor": "MediCare Supplies India",
            "domain": "Healthcare Supplies",
            "statutory_category": "Medicines & Safety Equipment",
            "rules": ["Line Discount Reconciliation", "GST 12%", "Account 5080/5010"]
        },
        {
            "id": "COMP-INV-007",
            "pdf_file": "COMP-INV-007_annual_saas_software_security.pdf",
            "json_file": "COMP-INV-007_annual_saas_software_security.json",
            "vendor": "CyberShield Security Systems Pvt Ltd",
            "domain": "Cybersecurity Software",
            "statutory_category": "Annual SaaS License",
            "rules": ["Software License 5040", "IGST 18%", "Multi-User License"]
        },
        {
            "id": "COMP-INV-008",
            "pdf_file": "COMP-INV-008_office_pantry_and_catering.pdf",
            "json_file": "COMP-INV-008_office_pantry_and_catering.json",
            "vendor": "Royal Hospitality & Pantry Services",
            "domain": "Corporate Catering",
            "statutory_category": "Statutory Blocked ITC (Section 17(5))",
            "rules": ["Section 17(5) ITC Ineligibility", "Tax Added to Expense (5080)", "Intra-State CGST+SGST"]
        },
        {
            "id": "COMP-INV-009",
            "pdf_file": "COMP-INV-009_industrial_heavy_machinery.pdf",
            "json_file": "COMP-INV-009_industrial_heavy_machinery.json",
            "vendor": "Bharat Industrial Fabricators",
            "domain": "Manufacturing & Machinery",
            "statutory_category": "Heavy Plant & Equipment Asset",
            "rules": ["High Value Capital Asset", "Account 1060/1050", "IGST 28%"]
        },
        {
            "id": "COMP-INV-010",
            "pdf_file": "COMP-INV-010_scanned_hvac_maintenance.pdf",
            "json_file": "COMP-INV-010_scanned_hvac_maintenance.json",
            "vendor": "ClimateControl Engineering Services",
            "domain": "Facility Maintenance",
            "statutory_category": "Scanned Document with OCR Path",
            "rules": ["RapidOCR Pipeline", "Table Layout Correction", "Account 5030 Repairs"]
        },
    ]

    # 2. Real-World & International Commercial Benchmarks (14 Vendors, 15 Documents)
    # 60% Train (8 vendors) / 40% Test (6 vendors)
    irl_train_vendors = [
        "Vertex Solutions LLC",
        "Dan Roberts",
        "Kruger & Weber GmbH",
        "TechStore Europe",
        "Consolidated Edison",
        "AT&T Telecommunications",
        "Central Perk Coffee Shop",
        "Roberts, Gonzalez and Davis",
    ]
    irl_test_vendors = [
        "CloudMetrics Technologies SL",
        "Contoso Ltd",
        "ABC Pvt Ltd",
        "Cobb, Allen and Diaz",
        "Paul, Wilson and Gonzalez",
        "Supermarket Retail",
    ]

    irl_invoices = [
        {
            "id": "IRL-INV-001",
            "pdf_file": "IRL-INV-001_tech_consultancy.pdf",
            "json_file": "IRL-INV-001_tech_consultancy.json",
            "vendor": "Vertex Solutions LLC",
            "domain": "US Tech Consultancy",
            "statutory_category": "USD Foreign Commercial",
            "rules": ["USD Foreign Currency", "Accounts Payable 2010"]
        },
        {
            "id": "IRL-INV-002",
            "pdf_file": "IRL-INV-002_uk_freelancer.pdf",
            "json_file": "IRL-INV-002_uk_freelancer.json",
            "vendor": "Dan Roberts",
            "domain": "UK Developer Services",
            "statutory_category": "GBP Foreign Commercial",
            "rules": ["GBP Foreign Currency", "Freelance Services"]
        },
        {
            "id": "IRL-INV-003",
            "pdf_file": "IRL-INV-003_german_supplier.pdf",
            "json_file": "IRL-INV-003_german_supplier.json",
            "vendor": "Kruger & Weber GmbH",
            "domain": "German Industrial Supply",
            "statutory_category": "EUR Foreign Commercial",
            "rules": ["EUR Foreign Currency", "Equipment Supply"]
        },
        {
            "id": "IRL-INV-004",
            "pdf_file": "IRL-INV-004_spanish_saas.pdf",
            "json_file": "IRL-INV-004_spanish_saas.json",
            "vendor": "CloudMetrics Technologies SL",
            "domain": "Spanish SaaS Analytics",
            "statutory_category": "EUR Multilingual Document",
            "rules": ["Multilingual RapidOCR", "EUR SaaS Subscription"]
        },
        {
            "id": "IRL-INV-005",
            "pdf_file": "IRL-INV-005_ecommerce.pdf",
            "json_file": "IRL-INV-005_ecommerce.json",
            "vendor": "TechStore Europe",
            "domain": "E-Commerce Retail",
            "statutory_category": "EUR Multi-Item Supply",
            "rules": ["Multi-Item Line Extraction", "Foreign EUR"]
        },
        {
            "id": "IRL-UTIL-001",
            "pdf_file": "IRL-UTIL-001_electric_coned.pdf",
            "json_file": None,
            "vendor": "Consolidated Edison",
            "domain": "Public Electric Utility",
            "statutory_category": "Utility Expense",
            "rules": ["Utility Bill Layout", "Electricity Expense"]
        },
        {
            "id": "IRL-UTIL-002",
            "pdf_file": "IRL-UTIL-002_telecom_att.pdf",
            "json_file": None,
            "vendor": "AT&T Telecommunications",
            "domain": "Telecommunications",
            "statutory_category": "Broadband / Phone Expense",
            "rules": ["Telecom Layout", "Monthly Utility"]
        },
        {
            "id": "IRL-REC-001",
            "pdf_file": "IRL-REC-001_coffee_shop.pdf",
            "json_file": None,
            "vendor": "Central Perk Coffee Shop",
            "domain": "Point-of-Sale Retail",
            "statutory_category": "POS Cash Receipt",
            "rules": ["POS Receipt Layout", "Immediate Settlement"]
        },
        {
            "id": "IRL-REC-002",
            "pdf_file": "IRL-REC-002_supermarket_retail.pdf",
            "json_file": None,
            "vendor": "Supermarket Retail",
            "domain": "Supermarket Retail",
            "statutory_category": "POS Retail Receipt",
            "rules": ["Thermal Paper POS Receipt"]
        },
        {
            "id": "IRL-BENCH-001",
            "pdf_file": "IRL-BENCH-001_contoso_billing.pdf",
            "json_file": None,
            "vendor": "Contoso Ltd",
            "domain": "Azure Cognitive Services Benchmark",
            "statutory_category": "Standard Cloud AI Benchmark",
            "rules": ["Azure Benchmark Baseline"]
        },
        {
            "id": "IRL-BENCH-002",
            "pdf_file": "IRL-BENCH-002_contoso_project_statement.pdf",
            "json_file": None,
            "vendor": "Contoso Ltd",
            "domain": "Azure Cognitive Services Benchmark",
            "statutory_category": "Project Statement Layout",
            "rules": ["Multi-Page Statement Baseline"]
        },
        {
            "id": "IRL-BENCH-003",
            "pdf_file": "IRL-BENCH-003_aws_minimalist.pdf",
            "json_file": None,
            "vendor": "ABC Pvt Ltd",
            "domain": "AWS Textract Benchmark",
            "statutory_category": "Minimalist Corporate Invoice",
            "rules": ["AWS Benchmark Baseline"]
        },
        {
            "id": "IRL-SCAN-001",
            "pdf_file": "IRL-SCAN-001_roberts_gonzalez.pdf",
            "json_file": None,
            "vendor": "Roberts, Gonzalez and Davis",
            "domain": "Hugging Face Donut Benchmark",
            "statutory_category": "Scanned Document with RapidOCR",
            "rules": ["Donut OCR Evaluation"]
        },
        {
            "id": "IRL-SCAN-002",
            "pdf_file": "IRL-SCAN-002_cobb_allen.pdf",
            "json_file": None,
            "vendor": "Cobb, Allen and Diaz",
            "domain": "Hugging Face Donut Benchmark",
            "statutory_category": "Single-Item Scanned Invoice",
            "rules": ["Single-Item OCR Evaluation"]
        },
        {
            "id": "IRL-SCAN-003",
            "pdf_file": "IRL-SCAN-003_paul_wilson.pdf",
            "json_file": None,
            "vendor": "Paul, Wilson and Gonzalez",
            "domain": "Hugging Face Donut Benchmark",
            "statutory_category": "Multi-Line Scanned Invoice",
            "rules": ["Multi-Line OCR Evaluation"]
        },
    ]

    # Combine vendor lists
    train_vendors = synth_train_vendors + irl_train_vendors
    test_vendors = synth_test_vendors + irl_test_vendors

    # Check vendor-disjoint condition: V_train ∩ V_test = ∅
    overlap = set(train_vendors).intersection(set(test_vendors))
    assert len(overlap) == 0, f"FATAL: Vendor leakage detected between train and test: {overlap}"

    # Partition invoices by vendor
    train_set = []
    test_set = []

    for inv in synth_invoices:
        inv["suite"] = "Synthetic Indian GST (Statutory)"
        inv["source_dir"] = str(SYNTH_DIR)
        if inv["vendor"] in synth_train_vendors:
            inv["split"] = "TRAIN_CALIBRATION"
            train_set.append(inv)
        elif inv["vendor"] in synth_test_vendors:
            inv["split"] = "TEST_EVALUATION"
            test_set.append(inv)

    for inv in irl_invoices:
        inv["suite"] = "Real-World Invoices & Benchmarks"
        inv["source_dir"] = str(IRL_DIR)
        if inv["vendor"] in irl_train_vendors:
            inv["split"] = "TRAIN_CALIBRATION"
            train_set.append(inv)
        elif inv["vendor"] in irl_test_vendors:
            inv["split"] = "TEST_EVALUATION"
            test_set.append(inv)

    manifest = {
        "protocol_name": "60_40_Vendor_Disjoint_Split",
        "split_ratio": {"train_pct": 60, "test_pct": 40},
        "guarantee": "Strict vendor-disjoint isolation (zero vendor overlap, no template memorization)",
        "summary": {
            "total_vendors": len(set(train_vendors + test_vendors)),
            "train_vendors_count": len(train_vendors),
            "test_vendors_count": len(test_vendors),
            "total_invoices": len(train_set) + len(test_set),
            "train_invoices_count": len(train_set),
            "test_invoices_count": len(test_set),
            "vendor_overlap_count": len(overlap),
        },
        "train_vendors": train_vendors,
        "test_vendors": test_vendors,
        "train_set": train_set,
        "test_set": test_set,
    }

    return manifest


def main():
    manifest = build_split()
    out_path = DATA_DIR / "vendor_split_manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("=" * 80)
    print("  VENDOR-DISJOINT 60-40 TRAIN/TEST SPLIT PROTOCOL GENERATED")
    print("=" * 80)
    summary = manifest["summary"]
    print(f"Total Unique Vendors:      {summary['total_vendors']}")
    print(f"Train/Calibration Vendors: {summary['train_vendors_count']} (60%)")
    print(f"Test/Evaluation Vendors:   {summary['test_vendors_count']} (40%)")
    print(f"Total Invoices:            {summary['total_invoices']}")
    print(f"  - Train Set Invoices:    {summary['train_invoices_count']}")
    print(f"  - Test Set Invoices:     {summary['test_invoices_count']}")
    print(f"Vendor Overlap:            {summary['vendor_overlap_count']} (STRICT ZERO LEAKAGE)")
    print(f"Saved Manifest:            {out_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
