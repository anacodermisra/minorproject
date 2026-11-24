# Curated Invoices for Manual UI Testing

This directory contains 20 authentic, pre-tested invoice PDF documents spanning every accounting scenario in your system.

### How to test:
1. Open the web UI in your browser: `http://localhost:5173`
2. Drag and drop any of the PDF files below into the upload dropzone.
3. Watch the system automatically parse tables, reconcile invariants, generate balanced double-entry proposals, and update the statutory Day Books and Trial Balance!

## Test Document Index

| # | File Name | Category | Rules Tested | Description |
|---|---|---|---|---|
| 01 | `01_INDIAN_GST_InterState_Bharat_Traders.pdf` | **Indian GST (HuggingFace Divya52)** | CGST/SGST/IGST routing, State Place of Supply, Line Arithmetic | Indian GST Inter-State (IGST 18%): IT & Office Supplies from Telangana to Delhi |
| 02 | `02_INDIAN_GST_IntraState_Commercial_Trading.pdf` | **Indian GST (HuggingFace Divya52)** | CGST/SGST/IGST routing, State Place of Supply, Line Arithmetic | Indian GST Intra-State (CGST 9% + SGST 9%): Local Commercial B2B Supply |
| 03 | `03_INDIAN_GST_MultiItem_Hardware_Retail.pdf` | **Indian GST (HuggingFace Divya52)** | CGST/SGST/IGST routing, State Place of Supply, Line Arithmetic | Indian GST Multi-Item Bill: Hardware Tools & Industrial Fasteners |
| 04 | `04_INDIAN_GST_Electronics_Workstation_Setup.pdf` | **Indian GST (HuggingFace Divya52)** | CGST/SGST/IGST routing, State Place of Supply, Line Arithmetic | Indian GST Clean Modern Layout: Computer Equipment & Peripherals |
| 05 | `05_INDIAN_GST_Office_Furniture_Assets.pdf` | **Indian GST (HuggingFace Divya52)** | CGST/SGST/IGST routing, State Place of Supply, Line Arithmetic | Indian GST Furniture & Ergonomic Seating (Capital Asset > Rs 10k) |
| 06 | `06_INDIAN_GST_Cloud_BareMetal_Hosting_88500.pdf` | **IT & Cloud Services** | Multi-slab GST, Capitalization (>Rs 10k), Blocked ITC Sec 17(5) | Monthly Dedicated Bare-Metal Servers & CDN (IGST 18%, Account 5040) |
| 07 | `07_INDIAN_GST_Dell_PowerEdge_Rack_Servers_377600.pdf` | **Capital Asset Acquisition** | Multi-slab GST, Capitalization (>Rs 10k), Blocked ITC Sec 17(5) | Enterprise Dell Rack Servers (Capital Asset > Rs 10k -> Account 1060 Computer Equipment) |
| 08 | `08_INDIAN_GST_Corporate_Legal_Retainer_53100.pdf` | **Legal & Professional Services** | Multi-slab GST, Capitalization (>Rs 10k), Blocked ITC Sec 17(5) | Quarterly Corporate Legal Retainer Fee (SAC 9982, Account 5070) |
| 09 | `09_INDIAN_GST_Express_Freight_Logistics_26250.pdf` | **Freight & Transport** | Multi-slab GST, Capitalization (>Rs 10k), Blocked ITC Sec 17(5) | Inter-State Freight & Cartage (SAC 9965, Account 5050) |
| 10 | `10_INDIAN_GST_Mixed_Assets_and_Cables_168150.pdf` | **Capitalization Threshold Split** | Multi-slab GST, Capitalization (>Rs 10k), Blocked ITC Sec 17(5) | Mixed High-Value PCs (Asset 1060) and Low-Value Cables (Expense 5060) |
| 11 | `11_INDIAN_GST_FirstAid_Kits_with_Discount_8960.pdf` | **Trade Discount & Health Expense** | Multi-slab GST, Capitalization (>Rs 10k), Blocked ITC Sec 17(5) | Multi-Item First Aid with Line-Item Trade Discount (GST 12%) |
| 12 | `12_INDIAN_GST_CyberSecurity_SaaS_License_188800.pdf` | **Software & Subscription** | Multi-slab GST, Capitalization (>Rs 10k), Blocked ITC Sec 17(5) | 50-User Endpoint Protection Annual SaaS Subscription (IGST 18%) |
| 13 | `13_INDIAN_GST_Pantry_Beverages_Blocked_ITC_16170.pdf` | **Statutory Blocked ITC** | Multi-slab GST, Capitalization (>Rs 10k), Blocked ITC Sec 17(5) | Roasted Coffee Beans & Pantry Snacks (Section 17(5) Blocked ITC -> Account 5080) |
| 14 | `14_INDIAN_GST_CNC_Lathe_Heavy_Machinery_640000.pdf` | **Heavy Equipment & Plant Asset** | Multi-slab GST, Capitalization (>Rs 10k), Blocked ITC Sec 17(5) | Industrial CNC Lathe Spindle Assembly (Asset Acquisition, Account 1050/1060) |
| 15 | `15_INDIAN_GST_Scanned_HVAC_Maintenance_25960.pdf` | **OCR Scanned Fallback Test** | Multi-slab GST, Capitalization (>Rs 10k), Blocked ITC Sec 17(5) | Scanned Paper Bill with Noise/Folds: Triggers RapidOCR Fallback Path |
| 16 | `16_GLOBAL_Vertex_Solutions_Consultancy_USD_8750.pdf` | **USD Global Invoice** | Foreign currency layout generalization, Immediate settlement | US Commercial B2B Tech Consultancy Invoice (Vertex Solutions LLC) |
| 17 | `17_GLOBAL_CloudMetrics_SaaS_EUR_2899.pdf` | **EUR Multilingual** | Foreign currency layout generalization, Immediate settlement | European SaaS Cloud Platform Invoice in Spanish (CloudMetrics SL) |
| 18 | `18_BENCHMARK_Azure_Contoso_Billing_USD_610.pdf` | **Cloud AI Benchmark** | Foreign currency layout generalization, Immediate settlement | Microsoft Azure Form Recognizer Official Standard Billing Benchmark |
| 19 | `19_BENCHMARK_AWS_Textract_ABC_Tax_Invoice_USD_6231.pdf` | **Cloud AI Benchmark** | Foreign currency layout generalization, Immediate settlement | AWS Textract Benchmark: Minimalist Corporate Tax Invoice |
| 20 | `20_REAL_WORLD_Retail_Coffee_Receipt_Cash_18.pdf` | **Cash & Bank Register** | Foreign currency layout generalization, Immediate settlement | Point-of-Sale Retail Receipt with Instant Settlement |
