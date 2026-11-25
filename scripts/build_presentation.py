import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# Styling Constants
COLOR_ORANGE = RGBColor(0xD2, 0x48, 0x17)      # #D24817 (Primary Brand / Accent)
COLOR_SLATE = RGBColor(0x1F, 0x29, 0x37)       # #1F2937 (Dark Slate text)
COLOR_MUTED = RGBColor(0x4B, 0x55, 0x63)       # #4B5563 (Secondary text)
COLOR_CARD_BG = RGBColor(0xF3, 0xF4, 0xF6)     # #F3F4F6 (Light Gray Card Background)
COLOR_CARD_BORDER = RGBColor(0xE5, 0xE7, 0xEB) # #E5E7EB (Subtle Border)
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)       # #FFFFFF (White)


def set_run(paragraph, text, font_name="Arial", size_pt=11, bold=False, color=COLOR_SLATE):
    """Adds or formats a run within a paragraph."""
    run = paragraph.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.color.rgb = color
    return run


def add_slide_header(slide, title_text):
    """Creates a consistent title box next to college logo on master layout."""
    tb = slide.shapes.add_textbox(Inches(2.35), Inches(0.30), Inches(7.30), Inches(0.85))
    tb.name = "Title 1"
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.name = "Arial"
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = COLOR_SLATE


def add_slide_number(slide, num_str):
    """Creates a circular badge slide number at bottom left (0.16, 6.79)."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.16), Inches(6.79), Inches(0.50), Inches(0.50)
    )
    shape.name = "Slide Number Placeholder 5"
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLOR_ORANGE
    shape.line.color.rgb = COLOR_ORANGE
    tf = shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = str(num_str)
    p.font.name = "Arial"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_WHITE
    p.alignment = PP_ALIGN.CENTER


def create_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER):
    """Creates a rounded rectangle card container."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    return card


def update_slide_number_badge(slide, num):
    """Finds existing slide number shape and updates its number, or adds one."""
    found = False
    for s in slide.shapes:
        if "slide number" in s.name.lower():
            if s.has_text_frame:
                s.text_frame.text = str(num)
                for p in s.text_frame.paragraphs:
                    p.alignment = PP_ALIGN.CENTER
                    for r in p.runs:
                        r.font.name = "Arial"
                        r.font.size = Pt(12)
                        r.font.bold = True
                        r.font.color.rgb = COLOR_WHITE
                found = True
                break
    if not found:
        add_slide_number(slide, num)


def build_updated_presentation():
    src_path = r"C:\Users\Anand\Downloads\finalreviewppt_original_backup.pptx"
    prs = Presentation(src_path)
    print(f"Loaded base presentation with {len(prs.slides)} slides.")

    # =========================================================================
    # SLIDE 2: PRESENTATION OVERVIEW (Update Agenda from 6 to 8 items)
    # =========================================================================
    slide2 = prs.slides[1]
    # Remove old badges and items
    shapes_to_remove = [
        s for s in slide2.shapes 
        if s.name.startswith("Badge ") or s.name.startswith("Item ")
    ]
    for s in shapes_to_remove:
        sp = s._element
        sp.getparent().remove(sp)

    agenda_items = [
        "Motivation & Industrial Problem",
        "Research Foundations & Base Papers (Rana et al. & Yao et al.)",
        "Proposed System Architecture & Multimodal Pipeline",
        "Statutory Accounting Intelligence & Enterprise Internal Controls",
        "Automated Bank & GSTR-2B IMS Reconciliation Engine",
        "Dataset, Evaluation Strategy & Empirical Benchmarks",
        "Live Full-Stack Demonstration (Vouchers, Ledger, BRS, Statements)",
        "Technology Stack, 48-Test Suite & Engineering Rigor"
    ]

    start_y = 1.35
    spacing = 0.62
    badge_size = 0.44

    for i, item_text in enumerate(agenda_items):
        cur_y = start_y + (i * spacing)
        # Badge
        badge = slide2.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(1.20), Inches(cur_y), Inches(badge_size), Inches(badge_size)
        )
        badge.name = f"Badge {i+1}"
        badge.fill.solid()
        badge.fill.fore_color.rgb = COLOR_ORANGE
        badge.line.color.rgb = COLOR_ORANGE
        tf_b = badge.text_frame
        tf_b.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf_b.margin_left = tf_b.margin_top = tf_b.margin_right = tf_b.margin_bottom = 0
        pb = tf_b.paragraphs[0]
        pb.text = str(i + 1)
        pb.font.name = "Arial"
        pb.font.size = Pt(13)
        pb.font.bold = True
        pb.font.color.rgb = COLOR_WHITE
        pb.alignment = PP_ALIGN.CENTER

        # Item Card / Text Box
        item_tb = slide2.shapes.add_textbox(
            Inches(1.85), Inches(cur_y - 0.04), Inches(7.30), Inches(badge_size + 0.08)
        )
        item_tb.name = f"Item {i+1}"
        tf_i = item_tb.text_frame
        tf_i.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf_i.word_wrap = True
        tf_i.margin_left = Inches(0.15)
        tf_i.margin_top = tf_i.margin_bottom = tf_i.margin_right = 0
        pi = tf_i.paragraphs[0]
        pi.text = item_text
        pi.font.name = "Arial"
        pi.font.size = Pt(14)
        pi.font.bold = True
        pi.font.color.rgb = COLOR_SLATE

    update_slide_number_badge(slide2, 2)
    print("Slide 2 (Overview) updated with 8 agenda items.")

    # =========================================================================
    # SLIDE 3: MOTIVATION & INDUSTRIAL PROBLEM (Enhance text)
    # =========================================================================
    slide3 = prs.slides[2]
    for s in slide3.shapes:
        if s.name == "Bottleneck":
            s.text_frame.clear()
            p1 = s.text_frame.paragraphs[0]
            set_run(p1, "THE MANUAL BOTTLENECK\n", size_pt=14, bold=True, color=COLOR_ORANGE)
            p2 = s.text_frame.add_paragraph()
            set_run(p2, "• Invoices arrive as heterogeneous scanned PDFs, digital receipts, and unstructured multi-page documents.\n", size_pt=11, color=COLOR_SLATE)
            set_run(p2, "• High-volume manual data entry causes cognitive fatigue, typo risks, and severe accounting backlogs in enterprise ERPs.", size_pt=11, color=COLOR_SLATE)
        elif s.name == "Gap":
            s.text_frame.clear()
            p1 = s.text_frame.paragraphs[0]
            set_run(p1, "THE GAP IN MODERN AI & LLMs\n", size_pt=14, bold=True, color=COLOR_ORANGE)
            p2 = s.text_frame.add_paragraph()
            set_run(p2, "• State-of-the-art Document AI (LayoutLM, Donut, standard VLMs) stops at key-value field extraction.\n", size_pt=11, color=COLOR_SLATE)
            set_run(p2, "• Unchecked LLMs hallucinate floating-point arithmetic and cannot produce balanced, auditor-verifiable double-entry books.", size_pt=11, color=COLOR_SLATE)
        elif s.name == "Challenge":
            s.text_frame.clear()
            p1 = s.text_frame.paragraphs[0]
            set_run(p1, "RESEARCH CHALLENGE & CORE OBJECTIVE\n", size_pt=14, bold=True, color=COLOR_ORANGE)
            p2 = s.text_frame.add_paragraph()
            set_run(p2, "How can we design a neuro-symbolic framework that combines template-free multimodal document extraction with deterministic accounting invariants (exact Decimal arithmetic, COA routing, and statutory tax rules) to automate financial ledger and statement generation?", size_pt=11, color=COLOR_SLATE)

    update_slide_number_badge(slide3, 3)
    print("Slide 3 (Motivation) updated.")

    # =========================================================================
    # SLIDE 4: RESEARCH FOUNDATIONS (Base Papers)
    # =========================================================================
    slide4 = prs.slides[3]
    for s in slide4.shapes:
        if s.name == "Paper 1":
            s.text_frame.clear()
            p = s.text_frame.paragraphs[0]
            set_run(p, "RANA ET AL. (2025) — JISEM\n", size_pt=13, bold=True, color=COLOR_ORANGE)
            p2 = s.text_frame.add_paragraph()
            set_run(p2, "• Focus: ", size_pt=11, bold=True, color=COLOR_SLATE)
            set_run(p2, "Template-free invoice digitization using SmolVLM with heuristic post-processing.\n", size_pt=11, color=COLOR_SLATE)
            set_run(p2, "• Strength: ", size_pt=11, bold=True, color=COLOR_SLATE)
            set_run(p2, "Eliminates supplier-specific templates with minimal computational footprint.\n", size_pt=11, color=COLOR_SLATE)
            set_run(p2, "• Limitation: ", size_pt=11, bold=True, color=COLOR_SLATE)
            set_run(p2, "Evaluated on private data; stops strictly at extraction without financial accounting integration.", size_pt=11, color=COLOR_SLATE)
        elif s.name == "Paper 2":
            s.text_frame.clear()
            p = s.text_frame.paragraphs[0]
            set_run(p, "YAO ET AL. (2026) — CANADIAN AI / PMLR\n", size_pt=13, bold=True, color=COLOR_ORANGE)
            p2 = s.text_frame.add_paragraph()
            set_run(p2, "• Focus: ", size_pt=11, bold=True, color=COLOR_SLATE)
            set_run(p2, "Multimodal document extraction with hybrid Markdown/HTML table layout correction.\n", size_pt=11, color=COLOR_SLATE)
            set_run(p2, "• Strength: ", size_pt=11, bold=True, color=COLOR_SLATE)
            set_run(p2, "Resolves column splitting and table cell boundaries (TEDS evaluation metric).\n", size_pt=11, color=COLOR_SLATE)
            set_run(p2, "• Limitation: ", size_pt=11, bold=True, color=COLOR_SLATE)
            set_run(p2, "Evaluated on paystubs and QA tasks; no double-entry ledger or financial reporting.", size_pt=11, color=COLOR_SLATE)
        elif s.name == "Contribution":
            s.text_frame.clear()
            p = s.text_frame.paragraphs[0]
            set_run(p, "OUR NEURO-SYMBOLIC CONTRIBUTION\n", size_pt=13, bold=True, color=COLOR_ORANGE)
            p2 = s.text_frame.add_paragraph()
            set_run(p2, "We bridge Rana et al.'s template-free extraction and Yao et al.'s table-layout corrector with a deterministic accounting invariant engine, statutory Indian GST/AS 10 rules, and automated BRS & GSTR-2B reconciliation.", size_pt=11, color=COLOR_SLATE)

    update_slide_number_badge(slide4, 4)
    print("Slide 4 (Research Foundations) updated.")

    # =========================================================================
    # SLIDE 5: SYSTEM ARCHITECTURE (Update 7 steps)
    # =========================================================================
    slide5 = prs.slides[4]
    step_details = {
        "Step 1 detail": "PyMuPDF digital extraction; OpenCV deskew + RapidOCR-ONNX page fallback for scanned PDFs.",
        "Step 2 detail": "Template-free vision-language parsing (SmolVLM / Multimodal VLM) with regex entity tagging.",
        "Step 3 detail": "Reconstruct column splits, isolate HSN/SAC codes, and strip merged summary footer contaminations.",
        "Step 4 detail": "Verify Qty × Rate = Line Total, Subtotal + Tax − Disc ± Round-off = Grand Total using exact Decimal.",
        "Step 5 detail": "Chart of Accounts mapping, Place of Supply GST routing, AS 10 capitalization, Section 17(5) blocked ITC.",
        "Step 6 detail": "Deterministic double-entry invariant guard: exact Σ Debits = Σ Credits = Grand Total with 0.00 float drift.",
        "Step 7 detail": "Maker-Checker 4-eyes approval, period locks, immutable general ledger, trial balance, and financial books."
    }
    for s in slide5.shapes:
        if s.name in step_details:
            s.text_frame.clear()
            p = s.text_frame.paragraphs[0]
            set_run(p, step_details[s.name], size_pt=10.5, color=COLOR_SLATE)

    update_slide_number_badge(slide5, 5)
    print("Slide 5 (Architecture) updated.")

    # =========================================================================
    # CREATE NEW SLIDE 6: STATUTORY COMPLIANCE & ENTERPRISE CONTROLS
    # =========================================================================
    slide6 = prs.slides.add_slide(prs.slide_masters[1].slide_layouts[0])
    add_slide_header(slide6, "Statutory Compliance & Enterprise Internal Controls")
    add_slide_number(slide6, 6)

    # Left Card: Statutory Tax & Asset Rules
    c1 = create_card(slide6, Inches(0.55), Inches(1.35), Inches(4.35), Inches(3.60))
    tb1 = slide6.shapes.add_textbox(Inches(0.70), Inches(1.45), Inches(4.05), Inches(3.40))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0
    p = tf1.paragraphs[0]
    set_run(p, "STATUTORY TAX & ASSET INTELLIGENCE\n", size_pt=12, bold=True, color=COLOR_ORANGE)
    p2 = tf1.add_paragraph()
    set_run(p2, "• AS 10 / Ind AS 16 Capitalization Threshold:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Supplies >₹10,000 unit cost with multi-year utility capitalize to Asset Accounts (1050/1060); supplies below threshold expense to P&L (5010/5060).\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• Section 17(5) Blocked ITC (CGST Act):\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Statutorily ineligible pantry, food, beverage, and personal supplies reroute tax into Account 5080 (Ineligible ITC Expense) preventing illicit claims.\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• Place of Supply Tax Routing (Section 16):\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Intra-state supplies split 50:50 into CGST (1081) + SGST (1082); inter-state routes to IGST (1083). Missing buyer GSTIN blocks credit.", size_pt=10, color=COLOR_MUTED)

    # Right Card: Enterprise Governance & Dual Controls
    c2 = create_card(slide6, Inches(5.10), Inches(1.35), Inches(4.35), Inches(3.60))
    tb2 = slide6.shapes.add_textbox(Inches(5.25), Inches(1.45), Inches(4.05), Inches(3.40))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_top = tf2.margin_right = tf2.margin_bottom = 0
    p = tf2.paragraphs[0]
    set_run(p, "ENTERPRISE GOVERNANCE & DUAL CONTROLS\n", size_pt=12, bold=True, color=COLOR_ORANGE)
    p2 = tf2.add_paragraph()
    set_run(p2, "• 4-Eyes Maker-Checker Dual Approval:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Voucher Preparer posts draft; authorized Approver validates or rejects, enforcing statutory segregation of financial duties.\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• Immutable Financial Period Locks:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Closed accounting periods reject back-dated postings to protect trial balance and historical audit integrity.\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• Statutory Contra Reversal Vouchers:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Posted transactions are legally immutable (no DELETE); corrections executed via contra reversal vouchers with an auditable trail.", size_pt=10, color=COLOR_MUTED)

    # Bottom Wide Card: Chart of Accounts & Rounding Parity
    c3 = create_card(slide6, Inches(0.55), Inches(5.10), Inches(8.90), Inches(1.45))
    tb3 = slide6.shapes.add_textbox(Inches(0.75), Inches(5.20), Inches(8.50), Inches(1.25))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    tf3.margin_left = tf3.margin_top = tf3.margin_right = tf3.margin_bottom = 0
    p = tf3.paragraphs[0]
    set_run(p, "CHART OF ACCOUNTS PARITY & FRACTIONAL VARIANCE\n", size_pt=12, bold=True, color=COLOR_ORANGE)
    p2 = tf3.add_paragraph()
    set_run(p2, "Multi-tier 4-digit Chart of Accounts (1000 Assets, 2000 Liabilities, 3000 Equity, 4000 Revenue, 5000 Expenses). Round-off variances (<±₹5.00) route strictly to Nominal Account 5090 (Rounding Off & Fractional Variance), ensuring exact parity with Accounts Payable.", size_pt=10.5, color=COLOR_SLATE)

    print("Slide 6 (Statutory & Controls) created.")

    # =========================================================================
    # CREATE NEW SLIDE 7: AUTOMATED BANK & GSTR-2B IMS RECONCILIATION
    # =========================================================================
    slide7 = prs.slides.add_slide(prs.slide_masters[1].slide_layouts[0])
    add_slide_header(slide7, "Automated Bank & GSTR-2B IMS Reconciliation")
    add_slide_number(slide7, 7)

    # Left Card: BRS Statement Engine
    c1 = create_card(slide7, Inches(0.55), Inches(1.35), Inches(4.35), Inches(3.60))
    tb1 = slide7.shapes.add_textbox(Inches(0.70), Inches(1.45), Inches(4.05), Inches(3.40))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0
    p = tf1.paragraphs[0]
    set_run(p, "BANK RECONCILIATION STATEMENT (BRS) ENGINE\n", size_pt=12, bold=True, color=COLOR_ORANGE)
    p2 = tf1.add_paragraph()
    set_run(p2, "• Mathematical BRS Equation Generator:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  B_adjusted = B_books + Uncredited Deposits − Unpresented Cheques − Bank Charges + Direct Credits.\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• Dynamic Passbook Equilibrium:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Automatically computes reconciled bank balances and isolates outstanding timing variances between books and bank statements.\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• Fuzzy Statement Auto-Match Service:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Matches bank lines to AP/AR vouchers using weighted confidence (Amount 0.50, Date 0.25, Reference/UTR 0.25) and auto-posts settlement vouchers.", size_pt=10, color=COLOR_MUTED)

    # Right Card: GSTR-2B & IMS Workspace
    c2 = create_card(slide7, Inches(5.10), Inches(1.35), Inches(4.35), Inches(3.60))
    tb2 = slide7.shapes.add_textbox(Inches(5.25), Inches(1.45), Inches(4.05), Inches(3.40))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_top = tf2.margin_right = tf2.margin_bottom = 0
    p = tf2.paragraphs[0]
    set_run(p, "GSTR-2B SCOPED RECONCILIATION & IMS\n", size_pt=12, bold=True, color=COLOR_ORANGE)
    p2 = tf2.add_paragraph()
    set_run(p2, "• 3-Way General Ledger Cross-Verification:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Reconciles internal purchase registers against official GSTR-2B returns for any target filing period (e.g., '102026').\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• Automatic Discrepancy Categorization:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Classifies line items into MATCHED, TAX_MISMATCH, INVOICE_MISSING_IN_BOOKS, and MISSING_IN_GSTR2B.\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• Official IMS Workspace Actions:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Supports ACCEPTED, REJECTED, and PENDING workflow actions, aligning internal ledgers directly with GST Portal directives.", size_pt=10, color=COLOR_MUTED)

    # Bottom Wide Card: Mathematical Determinism
    c3 = create_card(slide7, Inches(0.55), Inches(5.10), Inches(8.90), Inches(1.45))
    tb3 = slide7.shapes.add_textbox(Inches(0.75), Inches(5.20), Inches(8.50), Inches(1.25))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    tf3.margin_left = tf3.margin_top = tf3.margin_right = tf3.margin_bottom = 0
    p = tf3.paragraphs[0]
    set_run(p, "DECIMAL ARITHMETIC DETERMINISM & AUDIT READINESS\n", size_pt=12, bold=True, color=COLOR_ORANGE)
    p2 = tf3.add_paragraph()
    set_run(p2, "Arbitrary-precision Decimal arithmetic completely eliminates IEEE 754 binary floating-point drift (zero variance). Every bank clearance and tax reconciliation generates an immutable audit log entry recording timestamp, tenant, user ID, and before-and-after balances.", size_pt=10.5, color=COLOR_SLATE)

    print("Slide 7 (Reconciliation) created.")

    # Reorder slides so that Slide 6 and Slide 7 sit right after Slide 5:
    # Current slide order: [0..4 are S1..S5], 5 is S6(old S6), 6 is S7(old S7), 7 is S8(old S8), 8 is S9(old S9), 9 is new S6, 10 is new S7
    # We want new S6 at index 5 and new S7 at index 6.
    slide_ids = prs.slides._sldIdLst
    s7_id = slide_ids[-1]
    slide_ids.remove(s7_id)
    slide_ids.insert(5, s7_id) # insert at 5

    s6_id = slide_ids[-1]
    slide_ids.remove(s6_id)
    slide_ids.insert(5, s6_id) # insert at 5 (shifts s7_id to 6)

    print("Reordered slides: Slide 6 and Slide 7 placed in sequence.")

    # =========================================================================
    # SLIDE 8 (Old Slide 6): DATASET & EMPIRICAL EVALUATION STRATEGY
    # =========================================================================
    slide8 = prs.slides[7]
    for s in slide8.shapes:
        if s.name == "Data and evaluation":
            s.text_frame.clear()
            p = s.text_frame.paragraphs[0]
            set_run(p, "DATA SOURCES & LEAKAGE-FREE PROTOCOL\n", size_pt=13, bold=True, color=COLOR_ORANGE)
            p2 = s.text_frame.add_paragraph()
            set_run(p2, "• Public Benchmarks: ", size_pt=11, bold=True, color=COLOR_SLATE)
            set_run(p2, "CORD, SROIE, DocILE, and Azure/AWS benchmark baselines.\n", size_pt=11, color=COLOR_SLATE)
            set_run(p2, "• 20 Curated Indian Invoices: ", size_pt=11, bold=True, color=COLOR_SLATE)
            set_run(p2, "Covering multi-slab GST, thermal receipts, cloud hosting, heavy machinery, corporate retainers, and blocked ITC.\n", size_pt=11, color=COLOR_SLATE)
            set_run(p2, "• Leakage-Free Vendor-Disjoint Split: ", size_pt=11, bold=True, color=COLOR_SLATE)
            set_run(p2, "Strict zero vendor overlap (V_train ∩ V_test = ∅) proving true template-free generalization.", size_pt=11, color=COLOR_SLATE)

    update_slide_number_badge(slide8, 8)
    print("Slide 8 (Dataset & Evaluation) updated.")

    # =========================================================================
    # SLIDE 9 (Old Slide 7): LIVE FULL-STACK DEMONSTRATION
    # =========================================================================
    slide9 = prs.slides[8]
    # Update Demo steps to 7 comprehensive points matching Demo 1 to Demo 7 badges
    demo_steps = [
        ("Invoice Ingestion & Scanned OCR: ", "Multi-file drag-and-drop; SHA-256 deduplication and RapidOCR-ONNX fallback."),
        ("Dual-Pane Side-by-Side Reviewer: ", "Layout-preserved tables, isolated HSN codes, and proposed vouchers."),
        ("Double-Entry Invariant Guard: ", "Real-time badge proving Σ Debits = Σ Credits = Grand Total with 0.00 float drift."),
        ("4-Eyes Maker-Checker Dual Approval: ", "Voucher Preparer posts draft; authorized Checker reviews, edits, or approves."),
        ("General Ledger & Subsidiary Posting: ", "Atomic posting to SQLite/PostgreSQL with immutable sequence IDs."),
        ("Dynamic Trial Balance & Statements: ", "Verified debit-credit equality; live Trading, P&L, and Balance Sheet generation."),
        ("Automated BRS & GSTR-2B Workspace: ", "Bank statement fuzzy auto-matching and GSTR-2B IMS reconciliation actions.")
    ]
    # Update demo text boxes
    demo_idx = 0
    for s in slide9.shapes:
        if s.name.startswith("Demo ") and s.name.endswith(" text"):
            if demo_idx < len(demo_steps):
                s.text_frame.clear()
                p = s.text_frame.paragraphs[0]
                prefix, body = demo_steps[demo_idx]
                set_run(p, prefix, size_pt=10.5, bold=True, color=COLOR_SLATE)
                set_run(p, body, size_pt=10.5, color=COLOR_SLATE)
                demo_idx += 1

    update_slide_number_badge(slide9, 9)
    print("Slide 9 (Live Demo) updated.")

    # =========================================================================
    # SLIDE 10 (Old Slide 8): TECHNOLOGY STACK & ENGINEERING RIGOR
    # =========================================================================
    slide10 = prs.slides[9]
    tech_cards = {
        "Backend text": "Python 3.13 • FastAPI • Pydantic v2 (strict schemas & computed fields) • SQLAlchemy 2.0 (SQLite / PostgreSQL)",
        "Document Intelligence text": "PyMuPDF • SmolVLM / Multimodal VLM • RapidOCR-ONNX for image scans • Yao et al. TableLayoutCorrector",
        "Financial Integrity text": "Arbitrary-precision Decimal math (0.00 float drift) • AS 10 Capitalization (>₹10k) • Section 17(5) Blocked ITC • Maker-Checker • Period Locks",
        "Frontend text": "React 18 • Vite • Tailwind CSS v4 • Lucide Icons • Responsive Dual-Pane Reviewer",
        "Testing text": "48 Automated Pytest Tests Passing (100% Pass in 29.08s) across 6 test suites: Invariants, Extraction, DB Ledger, Rules Audit, Settlement, API Endpoints."
    }
    for s in slide10.shapes:
        if s.name in tech_cards:
            s.text_frame.clear()
            p = s.text_frame.paragraphs[0]
            set_run(p, tech_cards[s.name], size_pt=11, color=COLOR_SLATE)

    update_slide_number_badge(slide10, 10)
    print("Slide 10 (Tech Stack & 48 Tests) updated.")

    # =========================================================================
    # CREATE NEW SLIDE 11: PROJECT CONCLUSIONS & INDUSTRIAL ROADMAP
    # =========================================================================
    slide11 = prs.slides.add_slide(prs.slide_masters[1].slide_layouts[0])
    add_slide_header(slide11, "Project Conclusions & Industrial Roadmap")
    add_slide_number(slide11, 11)

    # Left Card: Key Research Achievements
    c1 = create_card(slide11, Inches(0.55), Inches(1.35), Inches(4.35), Inches(3.60))
    tb1 = slide11.shapes.add_textbox(Inches(0.70), Inches(1.45), Inches(4.05), Inches(3.40))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0
    p = tf1.paragraphs[0]
    set_run(p, "KEY RESEARCH ACHIEVEMENTS\n", size_pt=12, bold=True, color=COLOR_ORANGE)
    p2 = tf1.add_paragraph()
    set_run(p2, "• Neuro-Symbolic Invariant Architecture:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  First system unifying template-free multimodal VLM extraction with hard statutory accounting rules and double-entry invariants.\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• 100% Double-Entry Compliance:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Zero floating-point drift verified across all posted ledgers; mathematical balance (Σ Debits == Σ Credits) strictly maintained.\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• Rigorous Empirical Validation:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  48/48 automated tests passed in 29.08s; 90.91% blind evaluation pass rate across unconstrained scanned and multi-item invoices.", size_pt=10, color=COLOR_MUTED)

    # Right Card: Commercial & Industrial Impact
    c2 = create_card(slide11, Inches(5.10), Inches(1.35), Inches(4.35), Inches(3.60))
    tb2 = slide11.shapes.add_textbox(Inches(5.25), Inches(1.45), Inches(4.05), Inches(3.40))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_top = tf2.margin_right = tf2.margin_bottom = 0
    p = tf2.paragraphs[0]
    set_run(p, "COMMERCIAL & INDUSTRIAL IMPACT\n", size_pt=12, bold=True, color=COLOR_ORANGE)
    p2 = tf2.add_paragraph()
    set_run(p2, "• 85%+ Reduction in Turnaround Time:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Reduces manual invoice review from 10–15 minutes down to seconds, eliminating repetitive manual journal entry fatigue.\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• Elimination of Tax Compliance Fines:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Automated Section 17(5) blocked credit detection and GSTR-2B 3-way reconciliation prevent wrongful ITC claims and audit penalties.\n", size_pt=10, color=COLOR_MUTED)
    set_run(p2, "• Enterprise Audit-Ready Integrity:\n", size_pt=10.5, bold=True, color=COLOR_SLATE)
    set_run(p2, "  Maker-checker dual control, period locks, and immutable contra reversals ensure full statutory compliance under Indian Companies Act.", size_pt=10, color=COLOR_MUTED)

    # Bottom Wide Card: Industrial Roadmap & Next Steps
    c3 = create_card(slide11, Inches(0.55), Inches(5.10), Inches(8.90), Inches(1.45))
    tb3 = slide11.shapes.add_textbox(Inches(0.75), Inches(5.20), Inches(8.50), Inches(1.25))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    tf3.margin_left = tf3.margin_top = tf3.margin_right = tf3.margin_bottom = 0
    p = tf3.paragraphs[0]
    set_run(p, "FUTURE ROADMAP & PRODUCTION EXTENSIONS\n", size_pt=12, bold=True, color=COLOR_ORANGE)
    p2 = tf3.add_paragraph()
    set_run(p2, "1. Live GSTN API & e-Invoice QR Verification: Direct validation against Indian NIC e-Invoicing B2B portals.\n2. Foreign Exchange Multi-Currency: Automated IAS 21 unrealized forex gain/loss revaluation.\n3. Native ERP Connectors: Direct synchronization adapters for SAP S/4HANA, Tally Prime, and Zoho Books.", size_pt=10.5, color=COLOR_SLATE)

    # Reorder Slide 11 so it is placed before the Thank You slide (which is currently at index 10)
    slide_ids = prs.slides._sldIdLst
    s11_id = slide_ids[-1]
    slide_ids.remove(s11_id)
    slide_ids.insert(10, s11_id) # place at index 10, Thank You becomes index 11
    print("Slide 11 (Conclusions) created and inserted.")

    # =========================================================================
    # SLIDE 12 (Old Slide 9): THANK YOU & DEFENSE
    # =========================================================================
    slide12 = prs.slides[11]
    update_slide_number_badge(slide12, 12)
    print("Slide 12 (Thank You) updated.")

    # Save modified presentation
    dest_path = r"C:\Users\Anand\Downloads\finalreviewppt.pptx"
    prs.save(dest_path)
    print(f"\nPresentation successfully saved to: {dest_path}")
    print(f"Total slides in presentation: {len(prs.slides)}")


if __name__ == "__main__":
    build_updated_presentation()
