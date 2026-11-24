# B.Tech Minor Project Presentation Notes & Slide Blueprint

**Project Title:** Intelligent Invoice Processing for Automated Accounting Book Generation  
**Department:** Computer Science & Engineering, Bharati Vidyapeeth's College of Engineering (GGSIPU), New Delhi  
**Authors:** Anand Misra (04011502723), Pratham Nahata (05611502723)  
**Supervisor:** Dr. Jolly Parikh (Associate Professor)  
**Academic Cycle:** September – December 2026  
**System Live URL:** `http://localhost:5173` | **API Swagger Docs:** `http://127.0.0.1:8000/docs`

---

## Slide-by-Slide Presentation Blueprint

### Slide 1: Title & Team
* **Project Title:** Intelligent Invoice Processing for Automated Accounting Book Generation
* **Subtitle:** An End-to-End Multimodal Document Intelligence & Double-Entry Accounting Framework
* **Presenters:** Anand Misra (04011502723), Pratham Nahata (05611502723)
* **Guide:** Dr. Jolly Parikh, Associate Professor, Department of CSE

### Slide 2: Motivation & The Industrial Problem
* **The Manual Bottleneck:** Invoices arrive in heterogeneous formats (scanned, digital, multi-page, varied layouts). Accountants manually inspect, verify line items, determine GST treatments, and post double entries.
* **The Gap in Modern AI:** Existing state-of-the-art Document AI (LayoutLM, Donut, OCR pipelines) stops at **information extraction**. No system connects extracted tabular data directly to **verifiable double-entry accounting records** (Journals, Ledgers, Trial Balance, P&L, Balance Sheet).
* **Research Challenge:** How to achieve template-free extraction while enforcing strict financial invariants where LLMs are prone to arithmetic and accounting hallucinations.

### Slide 3: Research Foundations & Base Papers
* **Base Paper 1 (Rana et al., 2025 - JISEM):**
  * *Focus:* Template-free invoice digitization using SmolVLM + heuristic post-processing.
  * *Strength:* Lightweight VLM eliminates supplier-specific templates; low compute overhead.
  * *Limitation:* Tested on private data; stops at field extraction; no accounting integration.
* **Base Paper 2 (Yao et al., 2026 - Canadian AI / PMLR):**
  * *Focus:* Multimodal document extraction with table layout correction.
  * *Strength:* Hybrid Markdown/HTML representation fixes table header-row-column associations (evaluated with TEDS).
  * *Limitation:* Evaluated only on paystubs and QA tasks; no line-item reconciliation or financial ledger generation.
* **Our Contribution:** Unifying template-free extraction (Rana et al.) with multimodal table layout correction (Yao et al.) and coupling it with an **Accounting Interpretation & Deterministic Invariant Engine**.

### Slide 4: Proposed System Architecture (Methodology Flow)
* **Stage 1 (Ingestion & Preprocessing):** PDF vector text extraction or OpenCV deskew/contrast normalization for scans.
* **Stage 2 (Multimodal Extraction):** Template-free Vision-Language extraction (SmolVLM / Multimodal VLM).
* **Stage 3 (Table Layout Correction):** Hybrid Markdown/HTML row-column alignment to accurately associate descriptions, quantities, unit prices, and tax rates.
* **Stage 4 (Heuristic Validation):** Strict mathematical verification (Qty × Rate = Line Total, Subtotal + Tax − Discount = Grand Total).
* **Stage 5 (Accounting Interpretation):** LLM-assisted transaction classification and account mapping based on the Chart of Accounts and GST rules.
* **Stage 6 (Deterministic Accounting Engine):** Hardcoded double-entry invariant verification (Debits == Credits, exact decimal arithmetic, active COA accounts).
* **Stage 7 (Review & Financial Books):** Human-in-the-loop review UI, immutable Journal posting, Ledger generation, and automated Trial Balance / Financial Statements.

### Slide 5: Dataset & Evaluation Strategy
* **Data Sources:** Public invoice benchmarks (CORD, SROIE, DocILE) supplemented with synthetic, legally safe Indian GST invoices covering diverse layouts, tax slabs, and line items.
* **Leakage-Free Splitting:** Supplier/Template-disjoint train/test split (unseen vendors in test set) to prove true template-free generalization.
* **Ablation Studies (E1 to E6):**
  * E1: Baseline SmolVLM template-free extraction.
  * E2: SmolVLM + Rana et al. Heuristic Validation.
  * E3: Table Layout Correction (Yao et al. hybrid representation).
  * E4: Integrated Document Intelligence (Extraction + Correction + Validation).
  * E5: Full Pipeline with Accounting Interpretation.
  * E6: Complete End-to-End System with Deterministic Invariants & Human Review.

### Slide 6: Live Fullstack Demonstration
1. **Invoice Upload & Ingestion Screen:** User uploads PDF invoices (`INV-2026-001`, `INV-2026-002`, `INV-2026-003`).
2. **Side-by-Side Reviewer:** Shows extracted metadata, cleaned tables, and AI journal entry proposal side by side.
3. **Double-Entry Invariant Guard:** Real-time badge proving $\sum \text{Debits} == \sum \text{Credits} == \text{Grand Total}$.
4. **General Ledger Posting:** Atomically posts approved entry into SQLite/PostgreSQL ledger.
5. **Dynamic Trial Balance:** Real-time generation confirming debit and credit balance equality with 0 float drift.
6. **Financial Statements:** Live generated Profit & Loss Account and Balance Sheet.
7. **Compliance Audit Trail:** Displays immutable logbook of all document ingestions and user approvals.

### Slide 7: Technology Stack & Engineering Rigor
* **Backend:** Python 3.13, FastAPI, Pydantic v2 (strict typed schemas with computed fields), SQLAlchemy 2.0.
* **Financial Integrity:** Exact `Decimal` arithmetic (zero floating-point drift).
* **Document Intelligence:** PyMuPDF / pymupdf4llm layout parser, RapidOCR integration, Table Layout Corrector (Yao et al. hybrid model), Heuristic Extractor (Rana et al.).
* **Frontend:** React, Vite, Tailwind CSS v4, Lucide Icons.
* **Testing:** 43 automated Pytest unit and integration tests passing 100% in 6.00s.

---

## Slide 8: Viva Voce Defense & Examiner Q&A Playbook

### Q1: "How do you handle scanned invoices or poor quality PDFs without templates?"
**Answer:**
"Our ingestion pipeline employs a hybrid two-tier approach. For digital PDFs, `pymupdf4llm` extracts layout-preserved Markdown preserving tabular structure. For scanned documents or bitmap receipts, the system dynamically invokes `RapidOCR` to extract bounding boxes and text spans. Following extraction, our Table Layout Corrector (based on Yao et al., 2026) reconstructs broken table columns and strips footer/summary rows that commonly contaminate tabular line items."

### Q2: "Why can't you just use an LLM or Vision-Language Model for the whole pipeline including journal generation?"
**Answer:**
"Because language models are probabilistic and inherently hallucinate floating-point arithmetic and accounting codes. In financial accounting, an error of 1 paisa (₹0.01) invalidates the Trial Balance. Therefore, we use a hybrid neuro-symbolic architecture: Document AI / VLMs perform unstructured extraction, while a **deterministic invariant engine** written in Python using arbitrary-precision `Decimal` arithmetic enforces hard mathematical invariants ($\sum \text{Debits} == \sum \text{Credits}$, Line Item math, and statutory GST reconciliation). The AI proposes; deterministic code verifies."

### Q3: "What happens if an invoice has a round-off fraction? Where does that amount go?"
**Answer:**
"Under standard GAAP and Indian accounting conventions, rounding variances cannot be mixed into operating expenses or sales revenue. Our system routes rounding fractions ($<\pm \text{₹}5$) strictly to a dedicated Nominal Account: `5090 Rounding Off & Fractional Variance`. A positive round-off on purchase is debited as an expense variance, and a negative round-off is credited, maintaining exact mathematical parity between the invoice grand total and Accounts Payable."

### Q4: "Can a user delete a posted invoice from your database?"
**Answer:**
"No. Under Indian Companies Act (Section 128) and international auditing standards (GAAP / Ind AS), accounting ledgers are legally immutable once posted. Our API rejects any `DELETE` request for a posted document with an HTTP 400 error. If a transaction must be corrected or voided, the system provides a statutory reversal endpoint (`POST /api/journal/reverse/{entry_id}`) that creates an opposite contra journal entry (swapping Debits and Credits) and logs the full audit trail with the checker's identity."

### Q5: "How does your system prevent duplicate invoices from being paid or posted twice?"
**Answer:**
"We implement a defense-in-depth strategy:
1. **Ingestion Layer:** SHA-256 cryptographic hashing on incoming file payloads blocks identical files at upload time.
2. **Posting Layer:** A composite database check verifies that no active posted journal entry exists for the same `(tenant_id, invoice_number, vendor)` combination. Even if a user renames the file, the posting invariant stops duplicate ledger impact."

### Q6: "How do you handle Indian GST rules and Capitalization thresholds?"
**Answer:**
"Our Accounting Interpretation Engine models statutory Indian tax rules:
1. **Place of Supply vs Vendor State:** If POS matches supplier state, CGST (Code 1081) and SGST (Code 1082) are debited; if interstate, IGST (Code 1083) is debited.
2. **Capitalization:** Items exceeding ₹10,000 per unit with multi-year durability (e.g., conference tables, executive desks) are capitalized to Asset Accounts (`1050 Office Furniture`), whereas durable items below ₹10,000 are expensed under nature (`5010 Office Supplies` or `5060 Computer Peripherals`).
3. **Blocked ITC (Section 17(5)):** Ineligible items (personal consumption, employee transport) have tax amounts debited to `5080 Ineligible Input GST Expense` rather than claiming Input Tax Credit."

