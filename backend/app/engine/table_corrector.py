import re
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from app.schemas.invoice import InvoiceLineItem


class TableLayoutCorrector:
    """
    Implements Table Layout Correction inspired by Yao et al. (2026).
    Handles:
    - Merged summary footer cells (e.g. 'Total Tax (GST):<br>INR 2,160.00' in one cell)
    - Fragmented column splits (e.g. '500' and '.00' split across columns)
    - Isolating HSN/SAC codes from numerical calculations
    - Reconstructing Qty, Unit Price, Discount, and Total with mathematical alignment
    """

    SUMMARY_KEYWORDS = [
        "subtotal", "sub total", "sub-total", "taxable value", "taxable amount", "taxable", "merchandise subtotal", "base imponible", "zwischensumme", "net worth", "net amount",
        "total tax", "sales tax", "tax", "vat", "iva", "mwst", "ust", "cuota iva", "cgst", "sgst", "igst", "tax amount", "vat amount",
        "grand total", "total amount", "total due", "amount due", "invoice total", "total factura", "total con iva", "gesamtbetrag", "endbetrag", "net payable", "balance due", "previous balance", "total", "grossworth", "gross worth",
        "total discount", "discount", "rabatt", "descuento", "round off", "round-off"
    ]
    COMPRESSED_SUMMARY_KEYWORDS = [
        "subtotal", "taxablevalue", "taxableamount", "taxable", "merchandisesubtotal", "baseimponible",
        "totaltax", "salestax", "grandtotal", "totalamount", "totaldue", "invoicetotal", "totalfactura",
        "totaldiscount", "netpayable", "balancedue", "previousbalance", "roundoff"
    ]

    TAX_TABLE_HEADER_KEYWORDS = [
        "tax rate", "vat rate", "tipo iva", "steuersatz", "vat [%]", "tax base", "cuota iva", "grossworth", "gross worth"
    ]
    META_TABLE_HEADER_KEYWORDS = [
        "bill to", "ship to", "service address", "salesperson", "invoice details", "service location"
    ]

    METADATA_OR_HEADER_PATTERNS = [
        r"invoice\s*(?:no|num|number|date)",
        r"due\s*date",
        r"bill(?:ed)?\s*to",
        r"ship(?:ped)?\s*to",
        r"^\s*to\s*:",
        r"\bgstin\b",
        r"\bcode\s*:\s*\d{2}\b",
        r"^\s*tax\s*invoice\s*$",
        r"buyer\s*(?:gstin|name|details)",
        r"vendor\s*(?:gstin|name|details)",
        r"supplier\s*(?:gstin|name|details)",
        r"customer\s*(?:gstin|name|details)",
        r"place\s*of\s*supply",
        r"po\s*(?:no|number)",
        r"order\s*(?:no|number)",
        r"payment\s*terms",
        r"bank\s*details",
        r"account\s*number",
        r"ifsc\s*code",
        r"pan\s*(?:no|number)",
        r"item\s*description",
        r"^\s*description\s*$",
        r"^\s*particulars\s*$",
        r"^\s*hsn\s*/?\s*sac\s*$",
        r"^\s*qty\s*(?:<br>|unit)?\s*$",
        r"^\s*quantity\s*$",
        r"unit\s*price",
        r"^\s*rate\s*$",
        r"^\s*taxable\s*$",
        r"^\s*gst\s*%\s*$",
        r"^\s*igst\s*$",
        r"^\s*cgst\s*$",
        r"^\s*sgst\s*$",
        r"^\s*unit\s*$",
        r"^\s*total\s*(?:\(inr\))?\s*$",
        r"^\s*amount\s*$",
        r"^\s*s(?:r)?\.?\s*no\.?\s*$",
    ]

    @classmethod
    def is_metadata_or_header_row(cls, row_cells: List[str]) -> bool:
        if not row_cells:
            return True
        cleaned = [c.replace("*", "").replace("_", "").strip() for c in row_cells if c.strip()]
        if not cleaned:
            return True
        
        first_cell = cleaned[0].lower()
        # If first cell is a serial number (e.g. 1, 2, 01), it's definitely an item row
        if re.match(r"^\d{1,3}\.?$", first_cell):
            return False

        if first_cell in ("item description", "description", "particulars", "items", "item", "items purchased", "s.no", "sr.no", "sl no", "sl.no", "#"):
            return True

        if any(first_cell.startswith(k) for k in [
            "receipt", "date:", "time:", "cashier:", "register", "store", "phone:",
            "payment method", "authorization code", "cash tendered", "change due"
        ]):
            return True

        row_text = " ".join(cleaned).lower()
        if any(re.search(pat, row_text) for pat in cls.METADATA_OR_HEADER_PATTERNS):
            return True

        return False

    @staticmethod
    def extract_monetary_amount(text: str) -> Optional[Decimal]:
        if not text:
            return None
        stripped = text.strip().replace("*", "").replace("_", "")
        if stripped.endswith("%") or stripped in ("-", "—", "N/A", "NA"):
            return None

        matches = re.findall(r"\b(?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2}\b", text)
        if matches:
            cleaned = matches[-1].replace(",", "")
            try:
                return Decimal(cleaned).quantize(Decimal("0.01"))
            except Exception:
                pass
        
        comma_int_matches = re.findall(r"\b\d{1,3}(?:,\d{3})+\b", text)
        if comma_int_matches:
            try:
                return Decimal(comma_int_matches[-1].replace(",", "")).quantize(Decimal("0.01"))
            except Exception:
                pass

        int_matches = re.findall(r"\b\d+\b", text)
        if int_matches:
            try:
                return Decimal(int_matches[-1]).quantize(Decimal("0.01"))
            except Exception:
                pass
        return None

    @classmethod
    def classify_table(cls, table_str: str) -> str:
        lines = [l.strip() for l in table_str.strip().split("\n") if l.strip().startswith("|")]
        if not lines:
            return "EMPTY"
        
        # Check if any row in the table is an item header
        for line in lines:
            clean_l = line.lower().replace("*", "").replace("_", "")
            if any(k in clean_l for k in ["description", "descripción", "particulars", "training date", "item description", "product description"]):
                return "LINE_ITEMS"

        header = lines[0].lower().replace("*", "").replace("_", "")
        if any(k in header for k in cls.META_TABLE_HEADER_KEYWORDS):
            return "METADATA"
        if any(k in header for k in cls.TAX_TABLE_HEADER_KEYWORDS):
            return "TAX_SUMMARY"
        if len(lines) <= 5 and any(k in header for k in ["subtotal", "total", "merchandise subtotal"]):
            return "SUMMARY_FOOTER"
        return "LINE_ITEMS"

    @classmethod
    def is_summary_row(cls, row_cells: List[str]) -> bool:
        cleaned = [c.replace("*", "").replace("_", "").strip() for c in row_cells if c.strip()]
        if not cleaned:
            return False
        first_clean = cleaned[0].lower()
        if first_clean in (
            "subtotal", "sub-total", "sub total", "total", "grand total", "total due", "invoice total",
            "tax", "sales tax", "vat", "iva", "balance due", "merchandise subtotal", "base imponible",
            "total factura", "amount due", "previous balance", "total amount"
        ):
            return True
        row_text = " ".join(row_cells).lower().replace("*", "").replace("_", "")
        for kw in cls.SUMMARY_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", row_text):
                return True
        compressed = re.sub(r"[\s\*\_\-]+", "", row_text)
        return any(ckw in compressed for ckw in cls.COMPRESSED_SUMMARY_KEYWORDS)

    @classmethod
    def extract_summary_totals(cls, rows: List[List[str]]) -> Dict[str, Decimal]:
        totals: Dict[str, Decimal] = {}
        for row in rows:
            row_str = " ".join(row).lower().replace("*", "").replace("_", "")
            row_comp = re.sub(r"[\s\*\_\-]+", "", row_str)
            amt = None
            for cell in reversed(row):
                found = cls.extract_monetary_amount(cell)
                if found is not None:
                    amt = found
                    break

            if amt is not None:
                if any(k in row_str or k in row_comp for k in ["previousbalance", "prevbalance", "priorbalance", "balanceforward", "previousbal"]):
                    totals["previous_balance"] = amt
                elif any(k in row_str or k in row_comp for k in ["subtotal", "sub-total", "taxable", "baseimponible", "merchandisesubtotal", "zwischensumme", "netamount", "networth"]):
                    totals["subtotal"] = amt
                elif any(k in row_str or k in row_comp for k in ["totaltax", "salestax", "cgst", "sgst", "igst", "cuotaiva", "vat", "iva", "mwst", "ust", "tax"]):
                    totals["total_tax"] = totals.get("total_tax", Decimal("0.00")) + amt
                elif any(k in row_str or k in row_comp for k in ["discount", "totaldiscount", "rabatt", "descuento"]):
                    totals["total_discount"] = amt
                elif "round" in row_str or "round" in row_comp:
                    totals["round_off"] = amt
                elif any(k in row_str or k in row_comp for k in ["invoicetotal", "currentcharges", "currenttotal", "newcharges"]):
                    totals["invoice_total"] = amt
                elif any(k in row_str or k in row_comp for k in ["grandtotal", "totaldue", "amountdue", "totalfactura", "totalconiva", "gesamtbetrag", "endbetrag", "netpayable", "balancedue"]):
                    totals["grand_total"] = amt
                elif ("total" in row_str or "total" in row_comp) and not any(k in row_comp for k in ["tax", "discount", "subtotal", "base", "due"]):
                    totals["invoice_total"] = amt

        # Reconcile previous balance / statement balances with current invoice total
        if "previous_balance" in totals and totals["previous_balance"] > Decimal("0.00"):
            if "invoice_total" in totals:
                totals["grand_total"] = totals["invoice_total"]
            elif "grand_total" in totals and totals["grand_total"] > totals["previous_balance"]:
                totals["grand_total"] = totals["grand_total"] - totals["previous_balance"]
        elif "invoice_total" in totals and "grand_total" not in totals:
            totals["grand_total"] = totals["invoice_total"]
        elif "invoice_total" in totals and "subtotal" in totals:
            calc = totals["subtotal"] + totals.get("total_tax", Decimal("0.00")) - totals.get("total_discount", Decimal("0.00"))
            if abs(totals["invoice_total"] - calc) <= Decimal("0.05"):
                totals["grand_total"] = totals["invoice_total"]

        # Auto-reconcile tax if grand_total and subtotal are present but tax was given as a percentage without an explicit currency amount
        if "grand_total" in totals and "subtotal" in totals:
            if "total_tax" not in totals:
                diff = totals["grand_total"] - totals["subtotal"] + totals.get("total_discount", Decimal("0.00"))
                if diff > Decimal("0.00"):
                    totals["total_tax"] = diff

        return totals

    @classmethod
    def solve_line_numbers(cls, nums: List[Decimal]) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        """
        Robustly solves (qty, unit_price, discount_amount, total_amount) from arbitrary
        numerical tokens extracted from an invoice line item row.
        """
        if not nums:
            return Decimal("1.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00")
        if len(nums) == 1:
            return Decimal("1.00"), nums[0], Decimal("0.00"), nums[0]

        total_amt = nums[-1]

        # Check if any pair in nums multiplies to any other number in nums (handling internal arithmetic like 2 * 6.25 = 12.50)
        for i in reversed(range(len(nums))):
            target = nums[i]
            for j in range(len(nums)):
                if j == i:
                    continue
                for k in range(j + 1, len(nums)):
                    if k == i:
                        continue
                    q, p = nums[j], nums[k]
                    if abs((q * p) - target) <= Decimal("0.05"):
                        return q, p, Decimal("0.00"), target

        # Indian GST structure: [Price, Taxable, TaxRate, TaxAmt]
        if len(nums) == 4 and nums[1] >= nums[0] and abs((nums[1] * nums[2] / Decimal("100")) - nums[3]) <= Decimal("0.05"):
            unit_price = nums[0]
            line_total = nums[1]
            qty = (line_total / unit_price).quantize(Decimal("0.01")) if unit_price > 0 else Decimal("1.00")
            return qty, unit_price, Decimal("0.00"), line_total

        n = len(nums) - 1
        candidates = nums[:n]

        # 1. Percentage discount: q * p * (1 - d_pct/100) == total_amt
        for i in reversed(range(n)):
            for j in reversed(range(i)):
                q, p = candidates[j], candidates[i]
                for k in range(j + 1, n):
                    d_pct = candidates[k]
                    if 0 < d_pct < 100 and abs((q * p * (Decimal("1") - (d_pct / Decimal("100")))) - total_amt) <= Decimal("0.05"):
                        disc_amt = (q * p * d_pct / Decimal("100")).quantize(Decimal("0.01"))
                        return q, p, disc_amt, total_amt

        # 1b. Single price with percentage discount (implicit q=1): p * (1 - d_pct/100) == total_amt
        for i in reversed(range(n)):
            p = candidates[i]
            for k in range(i + 1, n):
                d_pct = candidates[k]
                if 0 < d_pct < 100 and abs((p * (Decimal("1") - (d_pct / Decimal("100")))) - total_amt) <= Decimal("0.05"):
                    disc_amt = (p * d_pct / Decimal("100")).quantize(Decimal("0.01"))
                    return Decimal("1.00"), p, disc_amt, total_amt

        # 2. Direct multiplication: q * p == total_amt
        for i in reversed(range(n)):
            for j in reversed(range(i)):
                q, p = candidates[j], candidates[i]
                if abs((q * p) - total_amt) <= Decimal("0.05"):
                    return q, p, Decimal("0.00"), total_amt

        # 3. Flat discount: (q * p) - d_amt == total_amt
        for i in reversed(range(n)):
            for j in reversed(range(i)):
                q, p = candidates[j], candidates[i]
                for k in range(j + 1, n):
                    d_amt = candidates[k]
                    if abs((q * p - d_amt) - total_amt) <= Decimal("0.05"):
                        return q, p, d_amt, total_amt

        # 4. Fallbacks based on token count
        if len(nums) == 2:
            if nums[0] == nums[1]:
                return Decimal("1.00"), nums[0], Decimal("0.00"), nums[1]
            return nums[0], (total_amt / nums[0]).quantize(Decimal("0.01")) if nums[0] > 0 else total_amt, Decimal("0.00"), total_amt

        if len(nums) == 3:
            if nums[0] == nums[2]:
                return Decimal("1.00"), nums[0], Decimal("0.00"), nums[2]
            return nums[0], nums[1], Decimal("0.00"), total_amt

        return nums[-3], nums[-2], Decimal("0.00"), total_amt

    @classmethod
    def reconstruct_table(cls, markdown_table: str) -> Tuple[List[InvoiceLineItem], Dict[str, Decimal]]:
        lines = [line.strip() for line in markdown_table.strip().split("\n") if line.strip()]
        if len(lines) < 2:
            return ([], {})

        parsed_rows: List[List[str]] = []
        for line in lines:
            if not line.startswith("|") or not line.endswith("|"):
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if cells and all(set(c).issubset({"-", ":", " "}) for c in cells):
                continue
            parsed_rows.append(cells)

        if not parsed_rows:
            return ([], {})

        # Locate header row if present
        header_idx = None
        for i, row in enumerate(parsed_rows):
            r_text = " ".join(row).lower().replace("*", "").replace("_", "")
            if any(k in r_text for k in ["description", "descripción", "particulars", "training date", "item description", "product description"]):
                header_idx = i
                break

        if header_idx is not None:
            candidate_rows = parsed_rows[header_idx + 1:]
        else:
            candidate_rows = parsed_rows[1:] if len(parsed_rows) > 1 else parsed_rows

        item_rows: List[List[str]] = []
        summary_rows: List[List[str]] = []
        seen_subtotal = False

        for row in candidate_rows:
            is_sum = cls.is_summary_row(row)
            if not seen_subtotal and is_sum:
                row_str = " ".join(row).lower()
                row_comp = re.sub(r"[\s\*\_\-]+", "", row_str)
                if any(k in row_str or k in row_comp for k in ["subtotal", "taxablevalue", "taxableamount", "taxable", "baseimponible", "merchandisesubtotal", "zwischensumme"]):
                    seen_subtotal = True

            if seen_subtotal or is_sum:
                summary_rows.append(row)
            elif cls.is_metadata_or_header_row(row):
                continue
            else:
                cleaned_cells = [c.replace("**", "").replace("*", "").strip() for c in row if c.strip()]
                if not cleaned_cells:
                    continue
                # If row is a receipt metadata/continuation row (e.g. SKU, Model, Qty line with empty second cell)
                first_cell = cleaned_cells[0].lower()
                if (len(cleaned_cells) == 1 or not row[-1].strip()) and any(first_cell.startswith(p) for p in ["sku:", "model:", "qty:", "phone:", "store", "receipt", "cashier", "time:", "date:"]):
                    if item_rows:
                        item_rows[-1][0] += " " + cleaned_cells[0]
                    continue
                item_rows.append(row)

        extracted_totals = cls.extract_summary_totals(summary_rows)

        line_items: List[InvoiceLineItem] = []
        for row in item_rows:
            cells = [re.sub(r"<[^>]+>", " ", c).replace("**", "").replace("*", "").strip() for c in row]
            if not cells:
                continue

            # Check if first cell is a serial number (e.g. '1', '01', '1.')
            if re.match(r"^\d{1,3}\.?$", cells[0]) and len(cells) > 1 and len(cells[1]) > 1:
                desc_parts = [cells[1]]
                rest = cells[2:]
            else:
                desc_parts = [cells[0]] if cells[0] else ["Item"]
                rest = cells[1:]

            if re.search(r"\b(?:qty|each|@|\u2192|->)\b", cells[0], re.I):
                full_rest = " ".join(cells)
            else:
                full_rest = " ".join(rest)

            # Isolate HSN/SAC code (4 to 8 digit integer not preceded by currency symbol and not followed by decimal point)
            hsn = None
            hsn_match = re.search(r"(?<![\$€£₹])\b(99\d{4}|\d{4,8})(?!\.\d+)\b", full_rest)
            if hsn_match:
                hsn = hsn_match.group(1)
                full_rest_clean = re.sub(r"\b" + re.escape(hsn) + r"\b", "", full_rest, count=1)
            else:
                full_rest_clean = full_rest

            # Check if rest contained word fragments of the description
            text_matches = re.findall(r"\b[A-Za-z]{2,}\b", full_rest_clean)
            if text_matches:
                valid_words = [
                    w for w in text_matches
                    if w.lower() not in ("pcs", "nos", "kg", "inr", "usd", "eur", "gst", "qty", "rate", "disc", "total")
                ]
                if valid_words:
                    desc_parts.append(" ".join(valid_words))

            desc = " ".join(desc_parts).strip()
            desc = re.sub(r"\s+", " ", desc)

            # Combine remaining columns and stitch together any fragmented decimal splits (like '500' and '.00')
            remaining_text = re.sub(r"(\d+)\s+(\.\d{2})", r"\1\2", full_rest_clean)

            # Extract numbers from remaining columns
            tokens = re.findall(r"\b(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?\b", remaining_text)
            nums: List[Decimal] = []
            for t in tokens:
                try:
                    nums.append(Decimal(t.replace(",", "")).quantize(Decimal("0.01")))
                except Exception:
                    pass

            # If no numbers were found in the row at all, treat as description continuation of prior item
            if not nums:
                if line_items and desc and desc != "Item":
                    line_items[-1].description += " " + desc
                continue

            qty, unit_price, discount, total_amt = cls.solve_line_numbers(nums)

            line_items.append(
                InvoiceLineItem(
                    description=desc,
                    hsn_sac=hsn,
                    quantity=qty if qty > Decimal("0.00") else Decimal("1.00"),
                    unit_price=unit_price,
                    discount_amount=discount,
                    total_amount=total_amt
                )
            )

        # Check summary rows for unlisted delivery/shipping/freight charges
        for s_row in summary_rows:
            s_text = " ".join(s_row).lower()
            if any(k in s_text for k in ["freight", "shipping", "delivery", "cartage"]) and not any(k in s_text for k in ["tax", "subtotal", "base"]):
                s_amt = None
                for c in reversed(s_row):
                    found = cls.extract_monetary_amount(c)
                    if found is not None:
                        s_amt = found
                        break
                if s_amt and s_amt > Decimal("0.00"):
                    # Only add if not already present in line items
                    if not any(abs(it.total_amount - s_amt) <= Decimal("0.05") for it in line_items):
                        line_items.append(
                            InvoiceLineItem(
                                description="Shipping, Freight & Handling Charges",
                                quantity=Decimal("1.00"),
                                unit_price=s_amt,
                                discount_amount=Decimal("0.00"),
                                total_amount=s_amt
                            )
                        )

        # Filter out empty/phantom line items with zero amount
        line_items = [
            it for it in line_items
            if it.total_amount > Decimal("0.00") or it.unit_price > Decimal("0.00")
        ]

        return (line_items, extracted_totals)
