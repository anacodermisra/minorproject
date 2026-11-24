import os
from decimal import Decimal
from typing import Optional, List, Dict
import pymupdf4llm

from app.schemas.invoice import ExtractedInvoice, ExtractionConfidence, InvoiceLineItem
from app.engine.table_corrector import TableLayoutCorrector
from app.engine.heuristics import HeuristicExtractor
from app.engine.invariants import validate_invoice_arithmetic
from app.engine.interpreter import get_financial_year


class DocumentIngestionService:
    """
    End-to-End Ingestion Service combining:
    - Base Paper 2 (Yao et al.): Hybrid Markdown layout representation + Table Layout Correction.
    - Base Paper 1 (Rana et al.): Template-free Heuristic field extraction & validation.
    - RapidOCR Support: Automatic optical character recognition for scanned/photo invoice documents.
    """

    @classmethod
    def process_pdf_invoice(cls, pdf_path: str) -> ExtractedInvoice:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Invoice document not found at: {pdf_path}")

        ext = os.path.splitext(pdf_path)[1].lower()
        # 1. Convert PDF or Image to layout-preserved Markdown (Yao et al. hybrid representation + RapidOCR)
        if ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"):
            import pymupdf
            img_doc = pymupdf.open(pdf_path)
            pdf_bytes = img_doc.convert_to_pdf()
            temp_pdf_path = pdf_path + ".temp.pdf"
            with open(temp_pdf_path, "wb") as f:
                f.write(pdf_bytes)
            try:
                raw_markdown = pymupdf4llm.to_markdown(temp_pdf_path)
            finally:
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
        else:
            raw_markdown = pymupdf4llm.to_markdown(pdf_path)

        # 2. Extract and Correct Table Layout
        # Segment markdown into distinct table blocks separated by non-table lines
        raw_tables = []
        curr_table = []
        for line in raw_markdown.split("\n"):
            if line.strip().startswith("|"):
                curr_table.append(line.strip())
            else:
                if curr_table:
                    raw_tables.append("\n".join(curr_table))
                    curr_table = []
        if curr_table:
            raw_tables.append("\n".join(curr_table))

        all_line_items = []
        merged_totals: Dict[str, Decimal] = {}

        for tbl_str in raw_tables:
            tbl_class = TableLayoutCorrector.classify_table(tbl_str)
            if tbl_class == "METADATA":
                continue
            elif tbl_class in ("TAX_SUMMARY", "SUMMARY_FOOTER"):
                # Extract summary totals without parsing as line items
                lines = [l.strip() for l in tbl_str.split("\n") if l.strip().startswith("|")]
                rows = []
                for l in lines:
                    cells = [c.strip() for c in l.split("|")[1:-1]]
                    if cells and not all(set(c).issubset({"-", ":", " "}) for c in cells):
                        rows.append(cells)
                summary_totals = TableLayoutCorrector.extract_summary_totals(rows)
                for k, v in summary_totals.items():
                    if k not in merged_totals or merged_totals[k] == Decimal("0.00"):
                        merged_totals[k] = v

                # Check if this summary footer has an unlisted freight/shipping charge
                for r in rows:
                    r_text = " ".join(r).lower()
                    if any(k in r_text for k in ["freight", "shipping", "delivery", "cartage"]) and not any(k in r_text for k in ["tax", "subtotal", "base"]):
                        s_amt = None
                        for c in reversed(r):
                            found = TableLayoutCorrector.extract_monetary_amount(c)
                            if found is not None:
                                s_amt = found
                                break
                        if s_amt and s_amt > Decimal("0.00"):
                            if not any(abs(it.total_amount - s_amt) <= Decimal("0.05") for it in all_line_items):
                                all_line_items.append(
                                    InvoiceLineItem(
                                        description="Shipping, Freight & Handling Charges",
                                        quantity=Decimal("1.00"),
                                        unit_price=s_amt,
                                        discount_amount=Decimal("0.00"),
                                        total_amount=s_amt
                                    )
                                )
            else:  # LINE_ITEMS
                items, totals = TableLayoutCorrector.reconstruct_table(tbl_str)
                all_line_items.extend(items)
                for k, v in totals.items():
                    if k not in merged_totals or merged_totals[k] == Decimal("0.00"):
                        merged_totals[k] = v

        line_items = all_line_items
        trapped_totals = merged_totals

        # 3. Extract Metadata via Heuristics (Rana et al.)
        inv_no = HeuristicExtractor.extract_invoice_number(raw_markdown)
        inv_date, due_date, is_fallback_date = HeuristicExtractor.extract_dates(raw_markdown)
        gstins = HeuristicExtractor.extract_gstin_tags(raw_markdown)
        vendor, buyer = HeuristicExtractor.extract_entity_names(raw_markdown)

        # Place of supply extraction
        pos = None
        pos_code = None
        import re
        pos_match = re.search(r"Place of Supply:\*?\*?\s*([^\n\|]+)", raw_markdown, re.IGNORECASE)
        if pos_match:
            pos = pos_match.group(1).replace("*", "").strip()
            code_match = re.search(r"\((\d{2})\)|\b(\d{2})\b", pos)
            if code_match:
                pos_code = code_match.group(1) or code_match.group(2)

        # 4. Resolve Totals
        subtotal = trapped_totals.get("subtotal")
        total_tax = trapped_totals.get("total_tax", Decimal("0.00"))
        total_discount = trapped_totals.get("total_discount", Decimal("0.00"))
        round_off = trapped_totals.get("round_off", Decimal("0.00"))
        grand_total = trapped_totals.get("grand_total")

        sum_lines = sum((item.total_amount for item in line_items), start=Decimal("0.00"))
        # If subtotal not directly extracted, compute sum of line items
        if not subtotal:
            subtotal = sum_lines
        elif line_items and grand_total is not None:
            # Reconcile partial subtotal (e.g. goods subtotal before freight line) when line items sum matches grand total
            if abs(sum_lines + total_tax - total_discount + round_off - grand_total) <= Decimal("0.05"):
                subtotal = sum_lines

        if not grand_total:
            grand_total = subtotal + total_tax - total_discount + round_off

        # 5. Construct Initial Normalized Model
        fy = get_financial_year(inv_date)
        validation_flags = []
        if is_fallback_date:
            validation_flags.append(
                f"Statutory Date Warning: Could not locate explicit invoice date in document. Defaulted to {inv_date} ({fy}). Verify date before posting to ensure correct Indian FY."
            )

        invoice = ExtractedInvoice(
            invoice_number=inv_no,
            invoice_date=inv_date,
            due_date=due_date,
            is_date_fallback=is_fallback_date,
            financial_year=fy,
            vendor_name=vendor,
            vendor_gstin=gstins.get("vendor_gstin"),
            buyer_name=buyer,
            buyer_gstin=gstins.get("buyer_gstin"),
            place_of_supply=pos,
            place_of_supply_state_code=pos_code,
            subtotal=subtotal,
            total_tax=total_tax,
            total_discount=total_discount,
            round_off=round_off,
            grand_total=grand_total,
            line_items=line_items,
            confidence=ExtractionConfidence.MEDIUM if is_fallback_date else ExtractionConfidence.HIGH,
            validation_flags=validation_flags
        )

        # 6. Apply Invariant Arithmetic Validation
        is_math_valid, math_warnings = validate_invoice_arithmetic(invoice)
        if not is_math_valid:
            invoice.confidence = ExtractionConfidence.LOW
            invoice.validation_flags.extend(math_warnings)
        elif math_warnings:
            invoice.validation_flags.extend(math_warnings)

        return invoice
