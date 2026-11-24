import re
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple


class HeuristicExtractor:
    """
    Template-free heuristic field extraction inspired by Rana et al. (2025).
    Extracts invoice numbers, dates, GSTINs, vendor and buyer information
    from unconstrained text and markdown streams using robust regex patterns.
    """

    GSTIN_PATTERN = r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b"
    INVOICE_NUM_PATTERNS = [
        r"(?:i?nvoice\s*no\.?|inv\s*#|invoice\s*number|bill\s*no\.?|invoice\s*id)[\s*:]+([A-Za-z0-9\-_/]+)",
        r"(?:factura|rechnung|recibo)\s*[:#\s]+([A-Za-z0-9\-_/]+)",
        r"\b(INV-[A-Za-z0-9\-_/]+)\b",
        r"\b([A-Z]{2,4}-\d{2,4}-\d{2,4})\b",
    ]
    DATE_PATTERNS = [
        r"(?:i?nvoice\s*date|date|dated)[\s*:]+(\d{4}-\d{2}-\d{2})",
        r"(?:i?nvoice\s*date|date|dated)[\s*:]+(\d{2}[/-]\d{2}[/-]\d{4})",
        r"\b(\d{4}-\d{2}-\d{2})\b",
        r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b",
    ]
    DUE_DATE_PATTERNS = [
        r"(?:due\s*date|payment\s*due)[\s*:]+(\d{4}-\d{2}-\d{2})",
        r"(?:due\s*date|payment\s*due)[\s*:]+(\d{2}[/-]\d{2}[/-]\d{4})",
    ]

    @classmethod
    def extract_gstin_tags(cls, text: str) -> Dict[str, Optional[str]]:
        gstins = re.findall(cls.GSTIN_PATTERN, text)
        result = {"vendor_gstin": None, "buyer_gstin": None}
        
        buyer_match = re.search(r"(?:buyer\s*gstin|customer\s*gstin)[\s*:]+(" + cls.GSTIN_PATTERN + ")", text, re.IGNORECASE)
        if buyer_match:
            result["buyer_gstin"] = buyer_match.group(1)
        
        vendor_match = re.search(r"(?:vendor\s*gstin|supplier\s*gstin|gstin)[\s*:]+(" + cls.GSTIN_PATTERN + ")", text, re.IGNORECASE)
        if vendor_match and vendor_match.group(1) != result["buyer_gstin"]:
            result["vendor_gstin"] = vendor_match.group(1)
        
        if not result["vendor_gstin"] and gstins:
            result["vendor_gstin"] = gstins[0]
        if not result["buyer_gstin"] and len(gstins) > 1:
            result["buyer_gstin"] = gstins[1]
            
        return result

    @classmethod
    def extract_invoice_number(cls, text: str) -> str:
        for pat in cls.INVOICE_NUM_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "UNKNOWN_INV"

    @classmethod
    def parse_date_safe(cls, date_str: str) -> date:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return date.today()

    @classmethod
    def extract_dates(cls, text: str) -> Tuple[date, Optional[date], bool]:
        """Returns (invoice_date, due_date, is_fallback_flag)"""
        inv_date = None
        due_date = None
        is_fallback = False

        for pat in cls.DATE_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                parsed = cls.parse_date_safe(match.group(1).strip())
                if parsed:
                    inv_date = parsed
                    break

        for pat in cls.DUE_DATE_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                due_date = cls.parse_date_safe(match.group(1).strip())
                break

        if not inv_date:
            inv_date = date.today()
            is_fallback = True

        return (inv_date, due_date, is_fallback)

    @classmethod
    def extract_entity_names(cls, text: str) -> Tuple[str, Optional[str]]:
        vendor_name = "Unknown Vendor"
        buyer_name = None

        # 1. Try markdown header `# **Company Name**`
        header_match = re.search(r"#\s*\*{0,2}(.*?)\*{0,2}\s*$", text, re.MULTILINE)
        if header_match:
            candidate = header_match.group(1).strip()
            if len(candidate) > 2 and "invoice" not in candidate.lower():
                vendor_name = candidate

        # 2. If vendor still unknown, check first bold block `**Company Name**` before GSTIN
        if vendor_name == "Unknown Vendor":
            bold_match = re.search(r"\*{2}([A-Za-z0-9\s&.,-]+?)\*{2}\s*(?:GSTIN|Address|\n)", text)
            if bold_match:
                candidate = bold_match.group(1).strip()
                if len(candidate) > 2 and "invoice" not in candidate.lower():
                    vendor_name = candidate

        # 3. Buyer extraction
        buyer_match = re.search(
            r"(?:billed\s*to|customer|buyer)[\s*:]+\*{0,2}([A-Za-z0-9\s.,&]+?)(?:\*{0,2}\s*(?:\n|\*\*|GSTIN|Invoice|Due))",
            text,
            re.IGNORECASE
        )
        if buyer_match:
            buyer_name = buyer_match.group(1).strip()

        return (vendor_name, buyer_name)
