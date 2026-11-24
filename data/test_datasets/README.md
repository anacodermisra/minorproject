# Invoice Test Datasets Collection

This directory contains two comprehensive invoice datasets tailored for testing document intelligence, layout-aware table extraction, OCR fallbacks, and deterministic double-entry accounting reconciliation.

---

## Directory Structure

```
data/test_datasets/
├── real_world_invoices/              # 15 Authentic / Real-World Documents & Benchmarks
│   ├── IRL-INV-001_tech_consultancy.pdf (+ .json)
│   ├── IRL-INV-002_uk_freelancer.pdf (+ .json)
│   ├── IRL-INV-003_german_supplier.pdf (+ .json)
│   ├── IRL-INV-004_spanish_saas.pdf (+ .json)
│   ├── IRL-INV-005_ecommerce.pdf (+ .json)
│   ├── IRL-REC-001_coffee_shop.pdf
│   ├── IRL-REC-002_supermarket_retail.pdf
│   ├── IRL-UTIL-001_electric_coned.pdf
│   ├── IRL-UTIL-002_telecom_att.pdf
│   ├── IRL-BENCH-001_contoso_billing.pdf
│   ├── IRL-BENCH-002_contoso_project_statement.pdf
│   ├── IRL-BENCH-003_aws_minimalist.pdf
│   ├── IRL-SCAN-001_roberts_gonzalez.pdf
│   ├── IRL-SCAN-002_cobb_allen.pdf
│   ├── IRL-SCAN-003_paul_wilson.pdf
│   ├── dataset_manifest.json
│   └── README.md
│
└── computer_generated_invoices/      # 10 Computer-Generated / Synthetic Edge-Case Invoices
    ├── COMP-INV-001_cloud_enterprise_hosting.pdf (+ .json)
    ├── COMP-INV-002_data_center_rack_servers.pdf (+ .json)
    ├── COMP-INV-003_legal_audit_consultancy.pdf (+ .json)
    ├── COMP-INV-004_logistics_and_express_freight.pdf (+ .json)
    ├── COMP-INV-005_mixed_it_peripherals_and_workstations.pdf (+ .json)
    ├── COMP-INV-006_pharmacy_and_firstaid_kit.pdf (+ .json)
    ├── COMP-INV-007_annual_saas_software_security.pdf (+ .json)
    ├── COMP-INV-008_office_pantry_and_catering.pdf (+ .json)
    ├── COMP-INV-009_industrial_heavy_machinery.pdf (+ .json)
    ├── COMP-INV-010_scanned_hvac_maintenance.pdf (+ .json)
    ├── dataset_manifest.json
    └── README.md
```

---

## 1. Real-World (IRL) Invoices (`real_world_invoices/`)

Curated real-world and benchmark datasets from verified open-source fixtures:
- **Invofox B2B Invoices & Receipts:** Real tech consultancy, freelance, European e-commerce, German equipment suppliers, retail store receipts, and utility bills (ConEd electricity, AT&T broadband) with ground-truth JSON annotations.
- **Azure Form Recognizer Benchmarks:** Contoso Ltd standard billing and project statement fixtures.
- **AWS Textract Benchmarks:** Minimalist commercial tax invoice with VAT/GSTIN.
- **KatanaML Donut Scanned Documents:** Real-world receipts and invoices converted into scanned PDF test fixtures to test OCR accuracy on non-digital pages.

---

## 2. Computer-Generated Invoices (`computer_generated_invoices/`)

Programmatically generated PDFs via ReportLab modeling the full spectrum of Indian accounting & GST scenarios:
- **Tax Slabs:** 5% (logistics & catering), 12% (medical supplies), 18% (IT software & legal), 28% (heavy industrial machinery).
- **Tax Regimes:** Intra-state (CGST + SGST) and Inter-state (IGST).
- **Asset Capitalization Rules:** Automatic capitalization of equipment > ₹10,000 threshold versus immediate expensing of consumables ≤ ₹10,000.
- **Discounts & Deductions:** Item-level and trade discounts.
- **OCR Stress Test:** `COMP-INV-010` is an image-only rasterized PDF without a text layer to exercise the RapidOCR fallback pipeline.
- **Ground Truth:** Each invoice has a corresponding `.json` file specifying exact line-items, tax amounts, and balanced double-entry journal lines.

---

## How to Test

### Via the Web UI:
1. Open the frontend at **http://localhost:5174**.
2. Sign in with `admin@example.com` / `admin123`.
3. In the **Invoices** tab, drag and drop any PDF from `data/test_datasets/real_world_invoices/` or `data/test_datasets/computer_generated_invoices/`.
4. Review the extracted header fields, line items, proposed double-entry journals, and post them to the ledger.

### Via API:
```bash
curl -X POST http://127.0.0.1:8011/api/documents/upload \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@data/test_datasets/computer_generated_invoices/COMP-INV-001_cloud_enterprise_hosting.pdf"
```
