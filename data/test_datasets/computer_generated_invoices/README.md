# Computer-Generated (Synthetic) Test Invoices

A benchmark suite of 10 computer-generated invoices covering all edge cases in GST calculation, asset capitalization thresholds, multi-rate tax brackets, discounts, and OCR fallback.

## Dataset Characteristics

- **Total Documents:** 10 comprehensive invoices
- **Tax Slabs Covered:** 5%, 12%, 18%, 28% GST, both Intra-State (CGST + SGST) and Inter-State (IGST)
- **Accounting Logic Covered:** Fixed Asset Capitalization (> ₹10k threshold), Consumables Expensing, Operating Software Subscriptions, Freight, Mixed Asset/Expense Split
- **OCR Fallback Coverage:** `COMP-INV-010` is an image-only scanned PDF to test the RapidOCR fallback pipeline
- **Ground Truth:** Every PDF has a paired `.json` file with full field-by-field and journal entry ground truth

## Inventory Table

| ID | File | Category | Total (INR) | Tax Structure | Extraction Engine |
|---|---|---|---|---|---|
| `COMP-INV-001_cloud_enterprise_hosting` | [COMP-INV-001_cloud_enterprise_hosting.pdf](COMP-INV-001_cloud_enterprise_hosting.pdf) | Technology & Hosting (Operating Expense) | INR 88,500.00 | IGST 18.0% | PyMuPDF Fast Text Layer |
| `COMP-INV-002_data_center_rack_servers` | [COMP-INV-002_data_center_rack_servers.pdf](COMP-INV-002_data_center_rack_servers.pdf) | Capital Equipment (Asset Purchase) | INR 377,600.00 | IGST 18.0% | PyMuPDF Fast Text Layer |
| `COMP-INV-003_legal_audit_consultancy` | [COMP-INV-003_legal_audit_consultancy.pdf](COMP-INV-003_legal_audit_consultancy.pdf) | Professional Fees (Operating Expense) | INR 53,100.00 | CGST 9.0%, SGST 9.0% | PyMuPDF Fast Text Layer |
| `COMP-INV-004_logistics_and_express_freight` | [COMP-INV-004_logistics_and_express_freight.pdf](COMP-INV-004_logistics_and_express_freight.pdf) | Freight & Shipping (Discounted Supply) | INR 26,250.00 | IGST 5.0% | PyMuPDF Fast Text Layer |
| `COMP-INV-005_mixed_it_peripherals_and_workstations` | [COMP-INV-005_mixed_it_peripherals_and_workstations.pdf](COMP-INV-005_mixed_it_peripherals_and_workstations.pdf) | Mixed Asset & Expense Invoice | INR 168,150.00 | CGST 9.0%, SGST 9.0% | PyMuPDF Fast Text Layer |
| `COMP-INV-006_pharmacy_and_firstaid_kit` | [COMP-INV-006_pharmacy_and_firstaid_kit.pdf](COMP-INV-006_pharmacy_and_firstaid_kit.pdf) | Health & Safety Consumables (12% GST) | INR 8,960.00 | CGST 6.0%, SGST 6.0% | PyMuPDF Fast Text Layer |
| `COMP-INV-007_annual_saas_software_security` | [COMP-INV-007_annual_saas_software_security.pdf](COMP-INV-007_annual_saas_software_security.pdf) | Software Subscriptions (Prepaid / Expense) | INR 188,800.00 | IGST 18.0% | PyMuPDF Fast Text Layer |
| `COMP-INV-008_office_pantry_and_catering` | [COMP-INV-008_office_pantry_and_catering.pdf](COMP-INV-008_office_pantry_and_catering.pdf) | Pantry & Refreshments (5% GST) | INR 16,170.00 | CGST 2.5%, SGST 2.5% | PyMuPDF Fast Text Layer |
| `COMP-INV-009_industrial_heavy_machinery` | [COMP-INV-009_industrial_heavy_machinery.pdf](COMP-INV-009_industrial_heavy_machinery.pdf) | Heavy Capital Machinery (28% GST) | INR 640,000.00 | IGST 28.0% | PyMuPDF Fast Text Layer |
| `COMP-INV-010_scanned_hvac_maintenance` | [COMP-INV-010_scanned_hvac_maintenance.pdf](COMP-INV-010_scanned_hvac_maintenance.pdf) | Repairs & Maintenance (Scanned Document) | INR 25,960.00 | CGST 9.0%, SGST 9.0% | RapidOCR Fallback |
