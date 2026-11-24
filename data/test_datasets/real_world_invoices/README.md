# Real-World (IRL) Invoice Test Dataset

Curated collection of authentic real-world invoices, receipts, utility bills, and scanned documents for testing invoice ingestion, table extraction, and accounting reconciliation.

## Dataset Summary

- **Total documents:** 15
- **Categories:** B2B Commercial Invoices, Cloud Benchmarks (Azure & AWS), Utility Bills, Retail Receipts, Scanned Documents (OCR).
- **Format:** All files are standard PDFs ready for direct upload and processing in the Accounting Automation UI (`http://localhost:5174`).

## Inventory & Index

| ID | File | Category | Currency | Total | Description | Path Tested |
|---|---|---|---|---|---|---|
| `IRL-INV-001_tech_consultancy` | [IRL-INV-001_tech_consultancy.pdf](IRL-INV-001_tech_consultancy.pdf) | B2B Commercial Invoices | USD | USD 8,750.00 | B2B Tech Consultancy Invoice (Vertex Solutions LLC) | PyMuPDF Text Layer |
| `IRL-INV-002_uk_freelancer` | [IRL-INV-002_uk_freelancer.pdf](IRL-INV-002_uk_freelancer.pdf) | B2B Commercial Invoices | GBP | GBP 3,750.00 | UK Freelance Developer Invoice (Dan Roberts) | PyMuPDF Text Layer |
| `IRL-INV-003_german_supplier` | [IRL-INV-003_german_supplier.pdf](IRL-INV-003_german_supplier.pdf) | B2B Commercial Invoices | EUR | EUR 12,480.00 | German Industrial Equipment & Parts Supplier (Kruger & Weber GmbH) | PyMuPDF Text Layer |
| `IRL-INV-004_spanish_saas` | [IRL-INV-004_spanish_saas.pdf](IRL-INV-004_spanish_saas.pdf) | B2B Commercial Invoices | EUR | EUR 2,899.00 | SaaS Software Subscription & Cloud Platform (CloudSphere SL) | PyMuPDF Text Layer |
| `IRL-INV-005_ecommerce` | [IRL-INV-005_ecommerce.pdf](IRL-INV-005_ecommerce.pdf) | B2B Commercial Invoices | EUR | EUR 1,435.50 | E-Commerce Multi-item Hardware & Logistics (TechStore Europe) | PyMuPDF Text Layer |
| `IRL-REC-001_coffee_shop` | [IRL-REC-001_coffee_shop.pdf](IRL-REC-001_coffee_shop.pdf) | Receipt | - | N/A | Retail Point-of-Sale Coffee Shop Receipt | PyMuPDF Text Layer |
| `IRL-REC-002_supermarket_retail` | [IRL-REC-002_supermarket_retail.pdf](IRL-REC-002_supermarket_retail.pdf) | Receipt | - | N/A | Supermarket Retail Purchase Receipt | PyMuPDF Text Layer |
| `IRL-UTIL-001_electric_coned` | [IRL-UTIL-001_electric_coned.pdf](IRL-UTIL-001_electric_coned.pdf) | Utility Bill | - | N/A | Consolidated Edison Electric Utility Bill | PyMuPDF Text Layer |
| `IRL-UTIL-002_telecom_att` | [IRL-UTIL-002_telecom_att.pdf](IRL-UTIL-002_telecom_att.pdf) | Utility Bill | - | N/A | AT&T Telecommunications & Broadband Monthly Bill | PyMuPDF Text Layer |
| `IRL-BENCH-001_contoso_billing` | [IRL-BENCH-001_contoso_billing.pdf](IRL-BENCH-001_contoso_billing.pdf) | Cloud Platform Benchmarks (Azure / AWS) | USD | USD 610.00 | Azure Form Recognizer Benchmark: Contoso Ltd Standard Billing | PyMuPDF Text Layer |
| `IRL-BENCH-002_contoso_project_statement` | [IRL-BENCH-002_contoso_project_statement.pdf](IRL-BENCH-002_contoso_project_statement.pdf) | Cloud Platform Benchmarks (Azure / AWS) | USD | USD 10,686.25 | Azure Form Recognizer Benchmark: Contoso Ltd Project Statement | PyMuPDF Text Layer |
| `IRL-BENCH-003_aws_minimalist` | [IRL-BENCH-003_aws_minimalist.pdf](IRL-BENCH-003_aws_minimalist.pdf) | Cloud Platform Benchmarks (Azure / AWS) | USD | USD 6,231.09 | AWS Textract Benchmark: ABC Pvt Ltd Minimalist Tax Invoice | PyMuPDF Text Layer |
| `IRL-SCAN-001_roberts_gonzalez` | [IRL-SCAN-001_roberts_gonzalez.pdf](IRL-SCAN-001_roberts_gonzalez.pdf) | Scanned Real-World Invoices (OCR Path) | USD | USD 3,120.51 | Scanned Invoice: Roberts, Gonzalez and Davis (4 line items, VAT) | OCR Fallback |
| `IRL-SCAN-002_cobb_allen` | [IRL-SCAN-002_cobb_allen.pdf](IRL-SCAN-002_cobb_allen.pdf) | Scanned Real-World Invoices (OCR Path) | USD | USD 60.45 | Scanned Single-Item Invoice: Cobb, Allen and Diaz | OCR Fallback |
| `IRL-SCAN-003_paul_wilson` | [IRL-SCAN-003_paul_wilson.pdf](IRL-SCAN-003_paul_wilson.pdf) | Scanned Real-World Invoices (OCR Path) | USD | USD 1,025.61 | Scanned Mid-range Commercial Invoice: Paul, Wilson and Gonzalez | OCR Fallback |

## Ground Truth Paired Files

Several documents (such as `IRL-INV-001` to `IRL-INV-005`) include paired `.json` ground-truth annotations detailing exact line-items, tax amounts, vendor and customer details, and total figures.
