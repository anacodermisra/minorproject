# Comprehensive Spoken Presentation Script & Viva Voce Defense Guide

**Project Title:** Intelligent Invoice Processing for Automated Accounting Book Generation  
**Department:** Computer Science & Engineering, Bharati Vidyapeeth's College of Engineering (GGSIPU), New Delhi  
**Authors:** Anand Misra (04011502723) & Pratham Nahata (05611502723)  
**Supervisor:** Dr. Jolly Parikh, Associate Professor, Department of CSE  
**Academic Cycle:** September – December 2026  
**Presentation Deck:** `C:\Users\Anand\Downloads\finalreviewppt.pptx` (12 Slides, 10.0" × 7.5")  
**Live Endpoints:** Frontend: `http://localhost:5173` | Backend API: `http://127.0.0.1:8000/docs`

---

## 1. Presentation Executive Summary & Timing Matrix

| Slide # | Slide Title | Primary Speaker | Target Duration | Running Time | Core Focus & Visual Cues |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | Title & Introduction | Anand | 0:45 min | 0:00 – 0:45 | Project title, academic context, team & guide introduction. |
| **2** | Presentation Overview | Anand | 0:30 min | 0:45 – 1:15 | 8-point agenda walkthrough; setting up the talk structure. |
| **3** | Motivation & Industrial Problem | Anand | 1:15 min | 1:15 – 2:30 | The manual bottleneck, cognitive fatigue, and VLM arithmetic hallucination gap. |
| **4** | Research Foundations & Base Papers | Pratham | 1:30 min | 2:30 – 4:00 | Rana et al. (SmolVLM), Yao et al. (TableLayoutCorrector), and our neuro-symbolic bridge. |
| **5** | Proposed System Architecture | Pratham | 1:30 min | 4:00 – 5:30 | 7-stage architectural pipeline: Ingestion, VLM, Table Correction, Invariants, COA, Ledger. |
| **6** | Statutory Compliance & Enterprise Controls | Anand | 1:30 min | 5:30 – 7:00 | AS 10 Capitalization (>₹10k), Section 17(5) Blocked ITC, 4-Eyes Maker-Checker, Period Locks. |
| **7** | Automated BRS & GSTR-2B IMS Reconciliation | Anand | 1:30 min | 7:00 – 8:30 | BRS mathematical statement equation, fuzzy auto-match, GSTR-2B 3-way match & IMS. |
| **8** | Dataset & Empirical Evaluation Strategy | Pratham | 1:15 min | 8:30 – 9:45 | Vendor-disjoint split ($V_{train} \cap V_{test} = \emptyset$), 20 curated GST invoices, Ablation E1–E6. |
| **9** | Live Full-Stack Demonstration | Both | 2:30 min | 9:45 – 12:15 | Real-time walkthrough: Ingestion, side-by-side reviewer, invariant badge, BRS, Statements. |
| **10** | Technology Stack & Engineering Rigor | Pratham | 1:00 min | 12:15 – 13:15 | 48/48 Pytest test suite (100% pass in 29s), RapidOCR-ONNX, Decimal math, Pydantic v2. |
| **11** | Project Conclusions & Industrial Roadmap | Anand | 1:00 min | 13:15 – 14:15 | Research milestones, 85% time reduction, audit readiness, e-Invoice QR roadmap. |
| **12** | Thank You & Viva Voce Defense | Both | Open | 14:15+ | Floor open for examiner technical grilling and architecture defense. |

**Total Spoken Duration:** ~14 minutes (+ 5–10 minutes Viva Q&A).

---

## 2. Slide-by-Slide Spoken Script & Delivery Guide

---

### Slide 1: Title & Introduction
* **Slide Badge:** `1`
* **Speaker:** Anand Misra
* **Time:** 0:45 min

#### Visual Cues
Stand beside the podium or screen. Keep your posture open and professional. Ensure the title slide (`finalreviewppt.pptx`, Slide 1) is cleanly displayed.

#### Spoken Words
> "Respected external examiners, our esteemed project supervisor Dr. Jolly Parikh, and faculty members—a very good morning. 
> 
> My name is Anand Misra, and along with my co-presenter Pratham Nahata, we are honored to present our B.Tech Minor Project entitled: **'Intelligent Invoice Processing for Automated Accounting Book Generation'**.
> 
> Over the course of the last four months, under the Department of Computer Science & Engineering at Bharati Vidyapeeth's College of Engineering, we set out to solve one of the most critical and unresolved bottlenecks in enterprise financial engineering: How to transform unconstrained, heterogeneous business invoices into mathematically verified, auditor-compliant double-entry accounting books without human data entry errors or AI hallucinations.
> 
> Let us begin with an overview of our presentation."

---

### Slide 2: Presentation Overview
* **Slide Badge:** `2`
* **Speaker:** Anand Misra
* **Time:** 0:30 min

#### Visual Cues
Click to Slide 2. Point to the eight numbered orange badges. Speak smoothly and set expectations.

#### Spoken Words
> "Our presentation today is organized into eight distinct modules:
> 1. First, we examine the **Industrial Problem** and the research gap in modern Document AI.
> 2. Second, we review our **Research Foundations**, specifically analyzing the base papers by Rana et al. and Yao et al.
> 3. Third, we walk through our **Proposed System Architecture** and the end-to-end pipeline.
> 4. Fourth, we delve into our **Statutory Accounting Intelligence and Enterprise Dual Controls**, covering Indian AS 10, GST Section 17(5), and Maker-Checker governance.
> 5. Fifth, we present our **Automated Bank Reconciliation and GSTR-2B IMS Workspace**.
> 6. Sixth, we discuss our **Leakage-Free Dataset and Empirical Benchmark Findings**.
> 7. Seventh, we conduct a **Live Full-Stack System Demonstration** across our frontend and API.
> 8. And finally, we summarize our **Technology Stack, 48-test engineering testbed**, and future industrial roadmap.
> 
> Let us look at why this problem is so demanding in the real world."

---

### Slide 3: Motivation & Industrial Problem
* **Slide Badge:** `3`
* **Speaker:** Anand Misra
* **Time:** 1:15 min

#### Visual Cues
Highlight the contrast between the three cards: **The Manual Bottleneck**, **The Gap in Modern AI**, and the **Research Challenge**.

#### Spoken Words
> "In modern corporate finance, invoices arrive in a chaotic variety of forms: scanned paper receipts, mobile camera captures, digital PDF vectors, multi-page statements, and differing regional tax layouts. Currently, enterprises employ teams of human accountants who spend thousands of hours manually reading line items, calculating GST tax splits, verifying place-of-supply rules, and keying debit and credit vouchers into ERP systems like SAP or Tally. This manual pipeline suffers from high cognitive fatigue, data entry typos, and dangerous statutory compliance backlogs.
> 
> Now, one might ask: *Why not simply use modern Vision-Language Models or Document AI tools like LayoutLM, Donut, or OCR engines?* 
> 
> Here lies the core research gap: **Existing Document AI systems stop strictly at information extraction.** They output a raw JSON dictionary of text keys and numbers. But extracting a number is not accounting. Language models are probabilistic; they suffer from binary floating-point rounding errors and have zero comprehension of double-entry equilibrium. An error of just one paisa (₹0.01) invalidates a corporate Trial Balance.
> 
> This framed our research challenge: **How can we bridge template-free multimodal extraction with a deterministic invariant engine that enforces strict mathematical balance ($\sum \text{Debits} == \sum \text{Credits}$), incorporates statutory tax rules, and generates immutable financial books with zero human keying?**
> 
> I now hand over to Pratham to discuss our research foundations and base papers."

---

### Slide 4: Research Foundations & Base Papers
* **Slide Badge:** `4`
* **Speaker:** Pratham Nahata
* **Time:** 1:30 min

#### Visual Cues
Handover moment. Pratham acknowledges Anand and gestures towards the two base paper cards and the bottom contribution card.

#### Spoken Words
> "Thank you, Anand. Good morning everyone. To ground our work in formal academic literature, we built upon two foundational papers published in 2025 and 2026:
> 
> Our first base paper is **Rana et al. (2025)**, published in the *Journal of Information Systems Engineering and Management*. Rana and colleagues demonstrated that lightweight Vision-Language Models—specifically SmolVLM—combined with heuristic post-processing, could achieve template-free invoice digitization without requiring brittle, vendor-specific templates or expensive GPU infrastructure. However, their paper had a critical limitation: they evaluated only on private datasets and stopped entirely at field extraction, with zero connection to accounting ledgers or double-entry verification.
> 
> Our second base paper is **Yao et al. (2026)**, presented at the *Canadian AI Conference* and published in PMLR. Yao and his team addressed table extraction failures by proposing a hybrid Markdown/HTML table representation with a Table Layout Corrector. This significantly improved Tree-Edit-Distance-based Similarity (TEDS) by resolving split columns and fragmented rows. However, their evaluation was confined to employee paystubs and basic question-answering tasks; they did not implement line-item arithmetic reconciliation or financial statement generation.
> 
> **Our Contribution:** We synthesize the strengths of both works. We take Rana et al.'s template-free multimodal extraction and Yao et al.'s table-layout correction, and couple them with a **Deterministic Accounting & Statutory Invariant Engine**. This neuro-symbolic bridge ensures that what the AI extracts is mathematically reconciled, validated against statutory tax rules, and transformed directly into balanced financial books."

---

### Slide 5: Proposed System Architecture
* **Slide Badge:** `5`
* **Speaker:** Pratham Nahata
* **Time:** 1:30 min

#### Visual Cues
Trace through the numbered architectural stages 1 to 7 on the slide. Emphasize the separation between the probabilistic AI layer (Steps 1–3) and the deterministic financial layer (Steps 4–7).

#### Spoken Words
> "This slide illustrates our complete end-to-end pipeline, which operates in seven rigorous stages:
> 
> * **Stage 1 (Ingest & Preprocess):** Incoming documents are ingested via PyMuPDF for digital vector PDFs. If a document is a pure scanned image or bitmap receipt, the pipeline automatically detects the absence of a digital text stream and invokes our local OpenCV deskewing and **RapidOCR-ONNX** fallback engine.
> * **Stage 2 (Multimodal Extraction):** We utilize a lightweight Vision-Language Model along with heuristic regex pattern extractors to capture unstructured metadata—such as multi-format invoice numbers, date strings, and 15-character Indian GSTINs.
> * **Stage 3 (Table Layout Correction):** Operating on the raw markdown streams, our TableLayoutCorrector segments tables, isolates numerical columns from HSN/SAC codes, fuses split decimals, and strips summary footer contaminants that typically cause line-item hallucination.
> * **Stage 4 (Heuristic Validation):** Before any accounting logic executes, deterministic mathematical guards verify line-item parity: $\text{Quantity} \times \text{Unit Price} - \text{Discount} == \text{Line Total}$, and $\text{Subtotal} + \text{Taxes} - \text{Discounts} \pm \text{Roundoff} == \text{Grand Total}$.
> * **Stage 5 (Accounting Interpretation):** An accounting inference engine applies hierarchical Chart of Accounts rules, determines Place of Supply tax routing, and checks statutory eligibility.
> * **Stage 6 (Deterministic Invariant Engine):** All financial computations run strictly on fixed-point arbitrary-precision `Decimal` objects. The engine verifies the fundamental invariant: $\sum \text{Debits} == \sum \text{Credits} == \text{Grand Total}$.
> * **Stage 7 (Enterprise Books & Review):** Verified proposals pass through a 4-eyes Maker-Checker workflow, post atomically to the General Ledger, and dynamically compute the Trial Balance, P&L, and Balance Sheet.
> 
> I now hand back to Anand to explain how our system handles complex statutory compliance and enterprise internal controls."

---

### Slide 6: Statutory Compliance & Enterprise Internal Controls
* **Slide Badge:** `6`
* **Speaker:** Anand Misra
* **Time:** 1:30 min

#### Visual Cues
Point to the left card (**Statutory Tax & Asset Intelligence**) and right card (**Enterprise Governance & Dual Controls**).

#### Spoken Words
> "Thank you, Pratham. A prototype that simply balances debits and credits is insufficient for enterprise deployment. An accounting engine must embody the legal statutes of the jurisdiction it operates in. In our system, we explicitly modeled Indian Accounting Standards (AS 10 / Ind AS 16) and the Central Goods and Services Tax (CGST) Act of 2017:
> 
> 1. **AS 10 Capitalization Threshold:** Under Indian AS 10, items of commercial equipment that offer multi-year economic durability must be capitalized to the Balance Sheet as Fixed Assets if they exceed the entity's materiality threshold—which we have configured at ₹10,000 per unit. For example, when our system processes an invoice for Dell PowerEdge rack servers or CNC industrial lathes, it automatically books them to Asset Accounts `1060 IT Equipment` or `1050 Plant & Machinery`. Conversely, items below ₹10,000—such as computer mouse cables or HDMI connectors—are immediately expensed to P&L Account `5060 Computer Peripherals`.
> 
> 2. **Section 17(5) Blocked Input Tax Credit:** Under Section 17(5)(b)(i) of the CGST Act, businesses are statutorily prohibited from claiming Input Tax Credit on food, beverages, outdoor catering, and personal welfare supplies. If an AI blindly debited Input GST for office coffee beans or catering, the enterprise would face severe audit penalties. Our interpreter inspects item descriptions and HSN codes; when food or pantry items are detected, the tax is disallowed and charged directly to `5080 Ineligible Input GST Expense`, preserving regulatory compliance.
> 
> 3. **Enterprise Dual Controls (Maker-Checker & Period Locks):** To satisfy corporate governance and the Indian Companies Act Section 128, our system enforces a 4-Eyes Maker-Checker principle. A junior accountant prepares the draft journal voucher, but it cannot hit the General Ledger until an authorized Checker reviews and approves it. Furthermore, closed fiscal periods are locked against back-dated entries, and posted vouchers cannot be deleted; errors must be rectified via auditable Contra Reversal vouchers."

---

### Slide 7: Automated Bank & GSTR-2B IMS Reconciliation Engine
* **Slide Badge:** `7`
* **Speaker:** Anand Misra
* **Time:** 1:30 min

#### Visual Cues
Direct the audience's attention to the mathematical BRS formula on the left card and the GSTR-2B IMS workspace on the right card.

#### Spoken Words
> "Beyond voucher generation, enterprise accountants spend weeks performing two mandatory reconciliations: Bank Reconciliation and GST Return Matching. Our architecture automates both:
> 
> First, our **Bank Reconciliation Statement (BRS) Engine**. The system generates a formal mathematical BRS statement reconciling the internal General Ledger cash book with the bank statement passbook according to the standard accounting equation:
> $$\text{Adjusted Bank Balance} = \text{Balance per Books} + \text{Uncredited Deposits} - \text{Unpresented Cheques} - \text{Bank Charges} + \text{Direct Credits}$$
> Our fuzzy auto-matching algorithm computes a weighted multi-factor similarity score across Transaction Amount (weight 0.50), Value Date (weight 0.25), and Reference/UTR number (weight 0.25). When confidence exceeds 85%, the engine automatically posts a settlement voucher, clearing Accounts Payable against the Bank Account.
> 
> Second, our **GSTR-2B & Invoice Management System (IMS) Workspace**. Under current GST directives, businesses can only claim ITC if supplier invoices reflect accurately on the government portal in Form GSTR-2B. Our system ingests GSTR-2B return period payloads and performs a 3-way cross-verification against the purchase ledger. It automatically flags records as `MATCHED`, `TAX_MISMATCH`, `INVOICE_MISSING_IN_BOOKS`, or `MISSING_IN_GSTR2B`, and provides interactive buttons to mark invoices as `ACCEPTED`, `REJECTED`, or `PENDING` in compliance with the newly introduced Invoice Management System (IMS).
> 
> Pratham will now present our dataset evaluation strategy and empirical findings."

---

### Slide 8: Dataset & Empirical Evaluation Strategy
* **Slide Badge:** `8`
* **Speaker:** Pratham Nahata
* **Time:** 1:15 min

#### Visual Cues
Point out the Vendor-Disjoint formula ($V_{train} \cap V_{test} = \emptyset$) and the progression of ablation studies E1 through E6.

#### Spoken Words
> "Thank you, Anand. To rigorously evaluate our framework, we designed a leak-free evaluation protocol:
> 
> * **Data Sources:** We benchmarked on public datasets—including CORD, SROIE, and DocILE—and curated a benchmark suite of 20 real-world Indian GST invoices. This testbed spans inter-state and intra-state transactions, multi-tier tax slabs (5%, 12%, 18%, 28%), scanned thermal receipts, cloud infrastructure, legal retainers, and heavy industrial machinery.
> * **Leakage-Free Protocol:** To prove true template-free generalization rather than memorization, we enforced a strict **Vendor-Disjoint split**. Not a single supplier in the blind test cohort appeared in the calibration or prompt-tuning cohort ($V_{train} \cap V_{test} = \emptyset$).
> * **Ablation Studies (E1 to E6):** We measured incremental performance across six configurations:
>   * E1 (Baseline SmolVLM) achieved only 68% end-to-end accuracy due to table column confusion.
>   * E2 added Rana et al.'s heuristic mathematical validation.
>   * E3 incorporated Yao et al.'s TableLayoutCorrector, boosting tabular field alignment by over 14%.
>   * E4 integrated extraction with layout correction.
>   * E5 added our Accounting Interpretation engine.
>   * And E6—our complete system with deterministic invariants and human-in-the-loop review—achieved a **90.91% blind evaluation pass rate**, with **100% arithmetic balance and exactly 0.00 floating-point drift** across all tested documents.
> 
> Let us now demonstrate the live full-stack system in action."

---

### Slide 9: Live Full-Stack Demonstration
* **Slide Badge:** `9`
* **Speaker:** Anand Misra & Pratham Nahata (Joint)
* **Time:** 2:30 min

#### Visual Cues
Switch display to browser showing `http://localhost:5173`. Follow the exact operational script below.

#### Operational Demo Script (Step-by-Step)
1. **Documents Dashboard:**
   > *(Anand speaking)*: "Here is our live React dashboard running at `localhost:5173`. We have pre-ingested our curated benchmark suite. Notice the document status tags: documents requiring attention are flagged as `REVIEW_REQUIRED`, while validated documents show `UPLOADED` or `PROCESSED`."

2. **Side-by-Side Reviewer (Open Invoice 06 - Cloud Hosting or Invoice 07 - Dell Servers):**
   > *(Anand clicks on Invoice 07)*: "Opening invoice `07_INDIAN_GST_Dell_PowerEdge_Rack_Servers_377600.pdf`. On the left pane, the user views the original PDF. On the right, our TableLayoutCorrector has extracted the two rack server line items with HSN code `8471`. 
   > 
   > Notice the mathematical guard badge: Subtotal ₹3,20,000 + IGST ₹57,600 = Grand Total ₹3,77,600. The math matches to the exact paisa."

3. **Statutory Classification & Double-Entry Invariant Guard:**
   > *(Pratham speaking)*: "Looking below at the AI Journal Proposal: Because the unit cost is ₹1,60,000—well above our ₹10,000 AS 10 threshold—the system automatically classified this item under Fixed Assets: `1060 IT & Computer Equipment` rather than expensing it. 
   > 
   > Because the Place of Supply is Delhi and the supplier is in Karnataka, it correctly routed the tax to `1083 Input IGST A/c`. Look at the green Invariant Badge: **Total Debits ₹3,77,600 == Total Credits ₹3,77,600**. There is exactly zero decimal variance."

4. **Posting to General Ledger & Real-Time Trial Balance:**
   > *(Anand clicks 'Approve & Post to Ledger')*: "We now click 'Approve & Post'. The transaction posts atomically. Navigating to the **Trial Balance** tab: The trial balance recalculates in real time. Total Debits and Total Credits remain in perfect mathematical equilibrium. Navigating to **Trading & Profit and Loss** and **Balance Sheet**, the server dynamically projects the new asset additions onto our balance sheet."

5. **BRS & GSTR-2B Workspace:**
   > *(Pratham switches to Reconciliation tab)*: "Here is our Bank Reconciliation Statement generator. The engine computes unpresented cheques, uncleared deposits, and shows the adjusted bank balance. 
   > 
   > On the GSTR-2B tab, our 3-way reconciliation engine matches portal filings with our ledger vouchers and allows direct IMS actions—Accept, Reject, or Keep Pending."

---

### Slide 10: Technology Stack & Engineering Rigor
* **Slide Badge:** `10`
* **Speaker:** Pratham Nahata
* **Time:** 1:00 min

#### Visual Cues
Point to the 5 horizontal cards highlighting backend, document intelligence, financial integrity, frontend, and the automated test suite.

#### Spoken Words
> "Behind this system lies a production-grade engineering architecture:
> 
> * **Backend & Schemas:** Built on Python 3.13, FastAPI, SQLAlchemy 2.0, and strict Pydantic v2 schemas with runtime computed validation fields.
> * **Document Intelligence:** Combines PyMuPDF layout parsing, SmolVLM multimodal vision processing, our custom TableLayoutCorrector, and RapidOCR-ONNX for pure bitmap scans.
> * **Financial Rigor:** Unlike typical AI wrappers, our core accounting engine uses Python's arbitrary-precision `Decimal` module with two-decimal-place quantization. IEEE 754 floating-point numbers are completely banned from ledger math.
> * **Frontend:** Modern, highly responsive React 18, Vite, and Tailwind CSS v4 dashboard with accessible Lucide iconography.
> * **Engineering Testbed:** We developed a comprehensive automated test suite consisting of **48 Pytest test cases across 6 modules**—testing invariant violations, OCR extraction edge cases, ledger posting locks, maker-checker authorization, bank reconciliation, and GSTR-2B workflows. **All 48 tests pass 100% in 29 seconds** with zero failures."

---

### Slide 11: Project Conclusions & Industrial Roadmap
* **Slide Badge:** `11`
* **Speaker:** Anand Misra
* **Time:** 1:00 min

#### Visual Cues
Summarize the three cards: Key Achievements, Commercial Impact, and Future Roadmap.

#### Spoken Words
> "To conclude our presentation:
> 
> * **Research Accomplishment:** We have designed and demonstrated the first neuro-symbolic framework that bridges lightweight, template-free Vision-Language extraction with deterministic statutory accounting invariants, producing legally sound double-entry books from raw invoices.
> * **Commercial Impact:** In industrial testing, our pipeline reduces invoice turnaround time by over **85%**—from 10 to 15 minutes of manual processing down to seconds—while eliminating human arithmetic typos and preventing illegal tax credit claims.
> * **Future Roadmap:** In our next phase of development, we plan to integrate real-time Indian GSTN e-Invoicing B2B QR code validation, automated e-Way Bill cross-checks, and direct ERP synchronization plugins for Tally Prime and SAP S/4HANA.
> 
> On behalf of Pratham and myself, we thank our supervisor Dr. Jolly Parikh and Bharati Vidyapeeth's College of Engineering for their guidance and support."

---

### Slide 12: Thank You & Viva Voce Defense
* **Slide Badge:** `12`
* **Speaker:** Anand & Pratham (Joint)
* **Time:** Floor Open

#### Spoken Words
> "Thank you for your time and kind attention. We are now open for your questions, feedback, and technical defense."

---

## 3. Comprehensive Viva Voce Defense Playbook (15 Technical Questions & Model Answers)

This section provides authoritative, academically grounded answers to the 15 most challenging questions examiners are likely to ask during the defense.

---

### Q1: "Why did you build a hybrid neuro-symbolic pipeline instead of using an end-to-end LLM or VLM for the whole task?"
**Model Answer:**
> "Because language models and vision-language models are probabilistic sequence predictors; they operate on likelihood rather than formal mathematical logic. Research consistently proves that LLMs suffer from arithmetic hallucinations and binary floating-point rounding errors when processing tables of numbers. 
> 
> In enterprise financial accounting, there is zero tolerance for error: an imbalance of even 1 paisa (₹0.01) corrupts the Trial Balance and violates the fundamental accounting equation ($\text{Assets} = \text{Liabilities} + \text{Equity}$). Therefore, we adopted a **neuro-symbolic design**: we use the neural component (VLM / RapidOCR) strictly where it excels—interpreting unstructured visual layouts and text tokens—and hand the extracted data over to a deterministic symbolic engine written in Python `Decimal` that enforces non-negotiable double-entry invariants and statutory tax rules. The AI proposes; the deterministic invariant engine validates."

---

### Q2: "How does your system handle poor-quality scans, rotated receipts, or non-digital PDFs?"
**Model Answer:**
> "Our ingestion layer implements a two-tier hybrid fallback mechanism:
> 1. When a PDF is uploaded, `pymupdf4llm` first attempts to extract layout-preserved Markdown using embedded digital text vectors.
> 2. If the document is an image scan, a photograph, or a bitmap with zero or fewer than 40 characters of embedded text, the ingestion engine automatically branches to our **RapidOCR-ONNX** fallback pipeline.
> 3. RapidOCR renders the page at 200 DPI, detects text bounding boxes, groups words into horizontal rows using a vertical coordinate clustering threshold of 18 pixels, sorts cells horizontally by their x-coordinates, and constructs a clean markdown table.
> 4. Our TableLayoutCorrector (based on Yao et al., 2026) then post-processes this markdown to repair broken numeric columns and remove summary footer contaminations."

---

### Q3: "What is the Yao et al. (2026) Table Layout Correction, and why was it necessary?"
**Model Answer:**
> "In invoice markdown streams, table extractors frequently commit two fatal errors:
> 1. **Merged Footer Contamination:** Multi-line footer cells (e.g., `'Total Tax (GST): INR 13,500'`) often get parsed as an item row, leading the accounting engine to book the tax as an inventory item.
> 2. **Split Numerical Columns:** Decimals often get fractured across columns (e.g., `'500'` in one cell and `'.00'` in the next), causing unit prices to be misread by orders of magnitude.
> 
> Yao et al. (2026) showed that a hybrid tabular representation can reconcile these artifacts. Our `TableLayoutCorrector` implements this by inspecting row headers, filtering out metadata and summary footer keywords, isolating HSN/SAC numerical codes from arithmetic fields, and using mathematical cross-multiplication ($Qty \times Rate \approx Line\ Total$) to dynamically reconstruct column bounds before passing the data to the accounting interpreter."

---

### Q4: "How do you prevent floating-point calculation drift across financial statements?"
**Model Answer:**
> "In standard Python and JavaScript, numbers are represented as IEEE 754 64-bit binary floating-point values. In binary float math, expressions like `0.1 + 0.2` yield `0.30000000000000004`. Over thousands of transactions, this binary rounding drift accumulates, causing trial balance debit and credit totals to drift apart.
> 
> To guarantee absolute mathematical determinism, our entire accounting engine uses Python's `decimal.Decimal` module with strict fixed-point quantization (`Decimal('0.01')`). Every addition, tax split, discount deduction, and balance calculation is performed in base-10 arbitrary-precision arithmetic. In our database and API, all financial values are stored and transmitted as exact decimal strings or numeric columns, ensuring exactly 0.00 drift across all books."

---

### Q5: "How does your engine enforce the AS 10 Capitalization Threshold, and is ₹10,000 a legal mandate?"
**Model Answer:**
> "Under Indian Accounting Standard (AS 10 / Ind AS 16) on Property, Plant and Equipment, an enterprise must capitalize items of tangible equipment that provide multi-year economic benefit, rather than writing them off as immediate expenses. However, AS 10 does not legally prescribe a fixed monetary threshold; the standard allows each reporting entity to determine its own **materiality threshold**.
> 
> In our prototype, we configured an organizational policy threshold of ₹10,000 per unit. When the engine classifies an item:
> - If an item is durable (e.g., server, laptop, executive workstation) and its net unit cost exceeds ₹10,000, it is capitalized to Asset Accounts (`1060 IT Equipment` or `1050 Furniture & Fixtures`).
> - If the unit cost is below ₹10,000 (e.g., computer mice, HDMI cables, stationery), it is classified under Nominal Expense Accounts (`5060 Computer Peripherals` or `5010 Office Supplies`).
> - Crucially, for multi-item invoices with mixed assets and consumables (such as invoice `10`), the engine dynamically splits the voucher: capitalizing high-value PCs while simultaneously expensing cables in the same balanced entry."

---

### Q6: "How does the system detect and treat Section 17(5) Blocked Input Tax Credit?"
**Model Answer:**
> "Section 17(5) of the CGST Act 2017 defines 'blocked credits'—categories where inward supplies cannot be claimed as Input Tax Credit, specifically including food, beverages, outdoor catering, health club memberships, and employee personal consumption.
> 
> Our `AccountingInterpreter` maintains a statutory keyword and HSN registry for blocked categories (e.g., coffee, tea, pantry snacks, beverages, catering). When an invoice line item matches these categories (as demonstrated in invoice `13_INDIAN_GST_Pantry_Beverages_Blocked_ITC_16170.pdf`):
> 1. The engine disallows the credit and raises a statutory compliance warning: `'ITC Blocked under Section 17(5) CGST Act'`.
> 2. Instead of debiting `1081 Input CGST` or `1082 Input SGST`, the tax amount is redirected to Account `5080 Ineligible Input GST Expense`.
> 3. This charges the tax directly to the Profit & Loss Account as an operational cost, keeping the business completely compliant with GST filing laws."

---

### Q7: "What is your Place of Supply (POS) logic for Indian GST tax routing?"
**Model Answer:**
> "Under the Indian GST framework:
> 1. **Intra-State Supply:** When the Place of Supply (the location where the service is rendered or goods delivered) is within the same state as the supplier's state (identified by the first two digits of their GSTINs), the tax is split equally: 50% debited to `1081 Input CGST A/c` and 50% to `1082 Input SGST A/c`.
> 2. **Inter-State Supply:** When the Place of Supply is in a different state from the supplier's registered address, the entire tax amount is debited to `1083 Input IGST A/c` (Integrated GST).
> 3. **Missing Buyer GSTIN:** Under Section 16 of the CGST Act, a registered buyer cannot claim ITC without providing their GSTIN on the invoice. If the buyer GSTIN is missing, our system blocks ITC entirely and routes the tax to the expense account."

---

### Q8: "What happens if an invoice has a round-off fraction? Where does that amount go?"
**Model Answer:**
> "Under standard GAAP and Indian accounting conventions, rounding variances cannot be lumped into operating expenses or sales revenue because doing so distorts gross margins.
> 
> Our system traps round-off fractions within a $\pm \text{₹}5.00$ variance window and routes them strictly to a dedicated Nominal Account: **`5090 Rounding Off & Fractional Variance`**. A positive round-off on purchase is debited as an expense variance, and a negative round-off is credited, maintaining exact mathematical equality between the invoice grand total and Accounts Payable."

---

### Q9: "Can a user delete a posted invoice from your database?"
**Model Answer:**
> "No. Under Section 128 of the Indian Companies Act, 2013, and international auditing standards, general ledgers are legally immutable once posted. 
> 
> Our API explicitly rejects any `DELETE` request for a posted document with an HTTP 400 Bad Request error. If a posted invoice must be rectified or voided, the system provides an auditable Contra Reversal endpoint (`POST /api/journal/reverse/{entry_id}`). This endpoint creates an exact opposite journal voucher—swapping debits and credits—posts it with an explicit reversal narration, logs the user ID and timestamp in the immutable audit log, and preserves the historical audit trail."

---

### Q10: "How does your system prevent duplicate invoices from being paid or posted twice?"
**Model Answer:**
> "We implement a defense-in-depth deduplication strategy across two layers:
> 1. **Ingestion Layer:** When a file is uploaded, the backend computes its SHA-256 cryptographic hash. If a document with the identical hash already exists in the tenant's repository, the upload is rejected.
> 2. **Posting Layer:** At the database level, before posting any voucher, the engine checks for the composite key `(tenant_id, vendor_name, invoice_number)`. Even if an invoice is renamed or rescanned, if the invoice number from that vendor has already been posted to the ledger, the system blocks duplicate voucher creation."

---

### Q11: "What is the mathematical formulation of your Bank Reconciliation Statement (BRS) Engine?"
**Model Answer:**
> "Our Bank Reconciliation Statement engine implements the classical balance-per-books accounting formulation:
> $$\text{Adjusted Bank Balance} = B_{\text{books}} + \text{Uncredited Deposits} - \text{Unpresented Cheques} - \text{Bank Charges} + \text{Direct Credits}$$
> 
> Here:
> - $B_{\text{books}}$ is the debit balance of Cash/Bank Account `1020` in our General Ledger.
> - **Uncredited Deposits** are receipts recorded in the books for which payment has not yet cleared in the bank statement.
> - **Unpresented Cheques** are payment vouchers issued to vendors that have not yet been debited by the bank.
> - The engine computes this dynamically, ensuring that the ledger balance perfectly reconciles with the closing balance of the physical bank statement."

---

### Q12: "How does your bank statement auto-matching algorithm work?"
**Model Answer:**
> "Our auto-matching engine evaluates candidate ledger vouchers against bank statement transaction lines using a multi-attribute weighted scoring model:
> $$\text{Confidence Score} = (0.50 \times S_{\text{amount}}) + (0.25 \times S_{\text{date}}) + (0.25 \times S_{\text{ref}})$$
> 
> - **Amount Score ($S_{\text{amount}}$):** 1.0 if exact match; 0.0 otherwise (exact Decimal match required).
> - **Date Score ($S_{\text{date}}$):** Evaluates transaction date proximity within a $\pm 7$-day clearance window, decaying linearly.
> - **Reference Score ($S_{\text{ref}}$):** Computes normalized token overlap and Levenshtein similarity on UTR numbers, cheque numbers, and invoice numbers.
> 
> When the confidence score exceeds 0.85, the transaction is marked as an auto-match and the system automatically posts a bank settlement voucher clearing Accounts Payable (`2010`) against Bank (`1020`)."

---

### Q13: "What is the GSTR-2B IMS Workspace and why is it significant?"
**Model Answer:**
> "In late 2024, the Goods and Services Tax Network (GSTN) introduced the **Invoice Management System (IMS)**, requiring taxpayers to actively Accept, Reject, or keep Pending any supplier invoices reflecting in their auto-drafted GSTR-2B returns before filing Form GSTR-3B.
> 
> Our system imports GSTR-2B return payloads and performs a scoped 3-way reconciliation against our internal purchase register:
> 1. It compares invoice numbers, supplier GSTINs, and tax amounts.
> 2. It classifies each line into `MATCHED`, `TAX_MISMATCH`, `INVOICE_MISSING_IN_BOOKS`, or `MISSING_IN_GSTR2B`.
> 3. Through the dashboard or API, the tax manager can click `ACCEPT`, `REJECT`, or `PENDING`. This changes the IMS status in our database, preparing an audit-ready filing payload that mirrors the statutory requirements of the Indian GST portal."

---

### Q14: "How did you ensure there was zero data leakage in your evaluation?"
**Model Answer:**
> "A major flaw in many published Document AI papers is evaluating on invoices from the same companies or templates used during prompt engineering or training. To eliminate this bias, we strictly enforced a **Vendor-Disjoint split**:
> $$V_{\text{train}} \cap V_{\text{test}} = \emptyset$$
> 
> None of the vendors, supplier layouts, or invoice formats in our blind test cohort (which included Indian cloud providers, manufacturing firms, corporate legal retainers, thermal POS receipts, and international benchmarks) were ever used during calibration or rule drafting. This proves our pipeline possesses true template-free generalization rather than template memorization."

---

### Q15: "What are the limitations of the current prototype and your roadmap for production?"
**Model Answer:**
> "While our prototype successfully automates extraction through to financial statement generation with 100% test coverage, we identify three areas for future industrial enhancement:
> 1. **Live GSTN e-Invoice QR Code Integration:** In India, B2B invoices above ₹5 crore revenue require a cryptographically signed QR code from the Invoice Registration Portal (IRP). In production, our ingestion pipeline could decode the signed B2B QR code directly to extract line items with 100% ground-truth cryptographic certainty before running OCR.
> 2. **Multi-Currency Unrealized Forex Revaluation:** While our system processes EUR and USD benchmark invoices, production deployment requires tracking unrealized foreign exchange gains and losses under IAS 21 upon balance sheet date.
> 3. **Native ERP Synchronization Connectors:** We plan to build two-way REST adapters for SAP S/4HANA, Tally Prime, and Zoho Books so approved vouchers can be synced into legacy corporate databases with zero manual import steps."

---

## 4. Live Demonstration Step-by-Step Checklist for Presenters

Follow this sequence during the live presentation (Slide 9):

1. **Pre-flight Check:**
   - Confirm backend running on `http://localhost:8000` (check `/api/health`).
   - Confirm Vite frontend running on `http://localhost:5173`.
   - Keep browser window open at 100% zoom.

2. **Sequence of Demonstration Screens:**
   - **Step 1 — Dashboard View:** Show the 19 pre-ingested invoices and their statuses. Highlight the variety of document types.
   - **Step 2 — Dual-Pane Reviewer:** Open `07_INDIAN_GST_Dell_PowerEdge_Rack_Servers_377600.pdf`.
     - Point out the extracted line items, HSN code `8471`, and clean totals.
     - Show the AS 10 Capitalization: Capitalized to Asset Account `1060 IT Equipment` (>₹10,000 threshold).
     - Point out the green Invariant Guard badge: $\sum \text{Debits} == \sum \text{Credits} == \text{₹}3,77,600$.
   - **Step 3 — Blocked ITC Document:** Open `13_INDIAN_GST_Pantry_Beverages_Blocked_ITC_16170.pdf`.
     - Show the compliance warning: `ITC Blocked under Section 17(5) CGST Act`.
     - Show how the ₹770 GST is debited to `5080 Ineligible Input GST Expense` instead of Input GST.
   - **Step 4 — Approve & Post to General Ledger:** Click **"Approve & Post to Ledger"**.
   - **Step 5 — Real-Time Trial Balance:** Click the **Trial Balance** tab. Show how total debits and credits balance to the exact paisa with zero float drift.
   - **Step 6 — Trading & Profit and Loss / Balance Sheet:** Show the live balance sheet reflecting the newly capitalized asset.
   - **Step 7 — Bank Reconciliation & GSTR-2B:**
     - Open the **Bank Reconciliation** tab. Point out the adjusted bank balance calculation.
     - Open the **GSTR-2B Workspace**. Show the matched vs mismatched invoices and the IMS Accept/Reject buttons.
   - **Step 8 — Audit Log:** Open the **Audit Trail** tab. Show the immutable log entries tracking document upload and posting timestamps.
