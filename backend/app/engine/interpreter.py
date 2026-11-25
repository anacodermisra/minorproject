import re
from decimal import Decimal
from datetime import date
from typing import List, Dict, Optional, Tuple, Set
from sqlalchemy.orm import Session

from app.schemas.invoice import ExtractedInvoice, InvoiceLineItem
from app.schemas.accounting import (
    ProposedJournalEntry,
    ProposedJournalLine,
    EntryType,
    TransactionType,
    AccountCategory,
    ValidationCheckStatus,
)


class AccountingPolicy:
    """
    Configurable entity-level accounting policies.
    
    NOTE: Capitalization threshold of INR 10,000 is an organization-level policy
    for this prototype based on materiality, NOT a mandated requirement of Indian
    Accounting Standards (AS 10 / Ind AS 16). Capitalization threshold and materiality
    must be determined by each reporting entity.
    """
    CAPITALIZATION_THRESHOLD = Decimal("10000.00")
    DEFAULT_ITC_ELIGIBLE = True

    # Section 17(5) CGST Act 2017: Statutory Blocked Input Tax Credits
    BLOCKED_ITC_KEYWORDS = [
        "food", "beverage", "beverages", "coffee", "tea", "milk", "snacks", "pantry", "refreshment",
        "catering", "outdoor catering", "club", "membership",
        "health service", "gym", "beauty", "cosmetic", "personal consumption",
        "motor vehicle", "car rental", "cab service"
    ]


class ItemClassificationRule:
    def __init__(
        self,
        name: str,
        category: str,
        account_code: str,
        account_name: str,
        account_category: AccountCategory,
        keywords: List[str],
        hsn_prefixes: List[str] = None,
        is_durable_asset: bool = False
    ):
        self.name = name
        self.category = category
        self.account_code = account_code
        self.account_name = account_name
        self.account_category = account_category
        self.keywords = [k.lower() for k in keywords]
        self.hsn_prefixes = hsn_prefixes or []
        self.is_durable_asset = is_durable_asset


def get_financial_year(dt: date) -> str:
    """Returns Indian Financial Year e.g. 'FY 2026-27' for April 1 to March 31."""
    if dt.month >= 4:
        start_year = dt.year
        end_year = (dt.year + 1) % 100
        return f"FY {start_year}-{end_year:02d}"
    else:
        start_year = dt.year - 1
        end_year = dt.year % 100
        return f"FY {start_year}-{end_year:02d}"


class AccountingInterpreter:
    """
    Semantic interpretation engine converting extracted invoices into
    verified double-entry journal proposals under Indian GST principles.
    """

    # Comprehensive, configurable classification rules
    RULES: List[ItemClassificationRule] = [
        # 1. Fixed Assets (Durable Furniture)
        ItemClassificationRule(
            name="Office Furniture",
            category="FURNITURE",
            account_code="1050",
            account_name="Office Furniture & Fixtures",
            account_category=AccountCategory.ASSET,
            keywords=["furniture", "table", "chair", "desk", "executive desk", "workstation table", "conference table", "ergonomic chair", "office chair", "filing cabinet", "cupboard", "almirah", "credenza"],
            hsn_prefixes=["9401", "9403"],
            is_durable_asset=True
        ),
        # 2. Capital IT & Computer Equipment
        ItemClassificationRule(
            name="IT Equipment Capital",
            category="IT_CAPITAL",
            account_code="1060",
            account_name="IT & Computer Equipment",
            account_category=AccountCategory.ASSET,
            keywords=["server", "laptop", "macbook", "workstation pc", "desktop computer", "computer", "monitor", "mainframe", "enterprise storage"],
            hsn_prefixes=["8471"],
            is_durable_asset=True
        ),
        # 3. Computer Accessories & Peripherals (Low-Value Equipment)
        ItemClassificationRule(
            name="Computer Accessories & Peripherals",
            category="PERIPHERALS",
            account_code="5060",
            account_name="Computer Accessories & Peripherals Expense",
            account_category=AccountCategory.EXPENSE,
            keywords=["docking station", "usb-c", "usb cable", "hdmi cable", "cable", "cables", "adapter", "adapters", "keyboard", "mouse", "webcam", "headset", "usb hub", "charger", "accessories", "peripherals"],
            hsn_prefixes=["8544", "8471", "8504"],
            is_durable_asset=False
        ),
        # 4. Office Supplies & Consumables
        ItemClassificationRule(
            name="Office Supplies & Stationery",
            category="SUPPLIES",
            account_code="5010",
            account_name="Office Supplies & Stationery",
            account_category=AccountCategory.EXPENSE,
            keywords=["paper", "copier paper", "a4 paper", "stationery", "pen", "notepad", "toner", "cartridge", "envelope", "binder", "stapler"],
            hsn_prefixes=["4802", "4820", "9608"],
            is_durable_asset=False
        ),
        # 5. Freight, Shipping & Delivery Charges
        ItemClassificationRule(
            name="Freight & Shipping",
            category="FREIGHT",
            account_code="5050",
            account_name="Freight, Shipping & Cartage Expense",
            account_category=AccountCategory.EXPENSE,
            keywords=["freight", "handling", "shipping", "delivery", "cartage", "transport", "courier", "consignment"],
            hsn_prefixes=["9965", "9968"],
            is_durable_asset=False
        ),
        # 6. Cloud, Hosting & Software Subscriptions
        ItemClassificationRule(
            name="Cloud & Software Expense",
            category="SOFTWARE",
            account_code="5020",
            account_name="Server, Cloud & Software Expense",
            account_category=AccountCategory.EXPENSE,
            keywords=["cloud", "hosting", "aws", "azure", "gcp", "saas", "software license", "subscription", "domain", "api"],
            hsn_prefixes=["9983", "9984"],
            is_durable_asset=False
        ),
        # 7. Rent & Premises
        ItemClassificationRule(
            name="Office Rent",
            category="RENT",
            account_code="5030",
            account_name="Office Rent Expense",
            account_category=AccountCategory.EXPENSE,
            keywords=["office rent", "premises lease", "rent", "workspace lease"],
            hsn_prefixes=["9972"],
            is_durable_asset=False
        ),
        # 8. Utilities
        ItemClassificationRule(
            name="Utilities",
            category="UTILITY",
            account_code="5040",
            account_name="Electricity & Utility Expense",
            account_category=AccountCategory.EXPENSE,
            keywords=["electricity", "power", "water", "broadband", "internet bill", "utility"],
            hsn_prefixes=["9969"],
            is_durable_asset=False
        ),
        # 9. Repairs & Maintenance
        ItemClassificationRule(
            name="Repairs & Maintenance",
            category="MAINTENANCE",
            account_code="5070",
            account_name="Repairs, Maintenance & Services Expense",
            account_category=AccountCategory.EXPENSE,
            keywords=["repair", "maintenance", "servicing", "amc", "upkeep", "hvac"],
            hsn_prefixes=["9987"],
            is_durable_asset=False
        ),
        # 10. Legal & Professional Fees
        ItemClassificationRule(
            name="Legal & Professional Fees",
            category="LEGAL_PROFESSIONAL",
            account_code="5070",
            account_name="Legal & Professional Services Expense",
            account_category=AccountCategory.EXPENSE,
            keywords=["legal", "retainer", "advocate", "consultancy", "professional fee", "solicitor", "audit fee", "consultant", "compliance retainer"],
            hsn_prefixes=["9982", "9983"],
            is_durable_asset=False
        ),
        # 11. Industrial Machinery & Plant Assets
        ItemClassificationRule(
            name="Plant & Machinery Capital Asset",
            category="MACHINERY",
            account_code="1050",
            account_name="Plant & Industrial Machinery",
            account_category=AccountCategory.ASSET,
            keywords=["machinery", "lathe", "laser cutting", "cnc", "industrial equipment", "manufacturing equipment"],
            hsn_prefixes=["8456", "8458", "8462"],
            is_durable_asset=True
        ),
        # 12. Medical & First-Aid Consumables
        ItemClassificationRule(
            name="Medical & Health Supplies",
            category="SUPPLIES",
            account_code="5010",
            account_name="Office Supplies & Welfare",
            account_category=AccountCategory.EXPENSE,
            keywords=["first aid", "first-aid", "medical", "pharmaceutical", "health kit"],
            hsn_prefixes=["3006"],
            is_durable_asset=False
        ),
        # 13. Software Licenses & CyberSecurity
        ItemClassificationRule(
            name="Software & CyberSecurity License",
            category="SOFTWARE",
            account_code="5020",
            account_name="Server, Cloud & Software Expense",
            account_category=AccountCategory.EXPENSE,
            keywords=["cybersecurity", "security software", "endpoint detection", "antivirus", "edr", "software license", "license"],
            hsn_prefixes=["998313"],
            is_durable_asset=False
        ),
        # 14. Pantry & Staff Welfare
        ItemClassificationRule(
            name="Pantry & Staff Welfare",
            category="WELFARE",
            account_code="5010",
            account_name="Office Pantry & Refreshments Expense",
            account_category=AccountCategory.EXPENSE,
            keywords=["coffee", "tea", "milk", "snacks", "pantry", "beverages", "refreshment"],
            hsn_prefixes=["2101", "0902", "1905"],
            is_durable_asset=False
        ),
    ]

    @classmethod
    def classify_line_item(
        cls,
        item: InvoiceLineItem,
        capitalization_threshold: Decimal = AccountingPolicy.CAPITALIZATION_THRESHOLD,
        business_type: str = "IT_SERVICES"
    ) -> Tuple[str, str, AccountCategory, str, bool]:
        """
        Classifies an item based on description, HSN code, nature, eligible cost,
        and entity commercial profile (business_type).
        Returns (account_code, account_name, account_category, explanation, requires_review).
        """
        desc_lower = item.description.lower()
        hsn = item.hsn_sac.strip() if item.hsn_sac else ""

        # Calculate unit eligible cost (net of line discount)
        unit_eligible_cost = item.unit_price
        if item.quantity > Decimal("0.00") and item.discount_amount > Decimal("0.00"):
            unit_eligible_cost = ((item.quantity * item.unit_price - item.discount_amount) / item.quantity).quantize(Decimal("0.01"))

        # Find matching rules
        matched_rule: Optional[ItemClassificationRule] = None

        for rule in cls.RULES:
            # Check HSN prefix match first (strong tax authority signal)
            if hsn and any(hsn.startswith(prefix) for prefix in rule.hsn_prefixes):
                matched_rule = rule
                break

            # Check keyword match
            if any(kw in desc_lower for kw in rule.keywords):
                matched_rule = rule
                break

        # 1. Ambiguous or completely unknown items
        if not matched_rule:
            return (
                "5010",
                "Office Supplies & Stationery",
                AccountCategory.EXPENSE,
                f"Item '{item.description}' could not be unambiguously mapped to a specific account category; routed to human review.",
                True
            )

        # 2. Context-Aware Accounting Policy: Commercial Entity Trading Inventory Rule
        # E.g. A stationery business buying stationery items treats them as Trading Inventory (COGS Account 5005),
        # whereas a technology or consulting company treats them as Operating Expenses (Account 5010).
        # A furniture store buying desks treats them as Trading Goods (5005), not Capital Fixed Assets!
        if business_type == "RETAIL_STATIONERY" and matched_rule.category == "SUPPLIES":
            explanation = (
                f"Domain-Aware Rule Applied: Entity is registered as '{business_type}'. "
                f"Stationery item '{item.description}' constitutes core merchandise purchased for resale "
                f"(COGS / Trading Goods Account 5005) rather than operational office consumables."
            )
            return ("5005", "Purchases of Trading Goods / COGS", AccountCategory.EXPENSE, explanation, False)

        if business_type == "FURNITURE_RETAILER" and matched_rule.category == "FURNITURE":
            explanation = (
                f"Domain-Aware Rule Applied: Entity is registered as '{business_type}'. "
                f"Furniture item '{item.description}' constitutes trading inventory held for commercial resale "
                f"(COGS Account 5005) rather than internal capitalized office fixtures."
            )
            return ("5005", "Purchases of Trading Goods / COGS", AccountCategory.EXPENSE, explanation, False)

        # 3. Capitalization Policy Evaluation for Durable Assets
        # Under AS 10 / Ind AS 16 and entity policy:
        # Capitalize ONLY if item is durable AND eligible unit cost is strictly greater than threshold (> 10,000)
        if matched_rule.is_durable_asset:
            if unit_eligible_cost > capitalization_threshold:
                explanation = (
                    f"Capitalized as Fixed Asset '{matched_rule.account_name}': "
                    f"Unit eligible cost (₹{unit_eligible_cost}) strictly exceeds capitalization threshold (₹{capitalization_threshold})."
                )
                return (matched_rule.account_code, matched_rule.account_name, AccountCategory.ASSET, explanation, False)
            else:
                # Durable item at or below threshold: do NOT automatically call it Office Supplies!
                # Classify according to nature:
                if matched_rule.category == "IT_CAPITAL":
                    explanation = (
                        f"Expensed as Computer Accessories & Peripherals: Unit cost (₹{unit_eligible_cost}) "
                        f"is at or below capitalization threshold (₹{capitalization_threshold})."
                    )
                    return ("5060", "Computer Accessories & Peripherals Expense", AccountCategory.EXPENSE, explanation, False)
                else:
                    explanation = (
                        f"Expensed as Low-Value Office Equipment / Supplies: Unit cost (₹{unit_eligible_cost}) "
                        f"is at or below capitalization threshold (₹{capitalization_threshold})."
                    )
                    return ("5010", "Office Supplies & Stationery", AccountCategory.EXPENSE, explanation, False)

        # 4. Operating Expenses & Revenue Items
        explanation = f"Expensed under '{matched_rule.account_name}' based on nature of item ({matched_rule.name})."
        return (matched_rule.account_code, matched_rule.account_name, matched_rule.account_category, explanation, False)

    @classmethod
    def evaluate_itc_eligibility(cls, invoice: ExtractedInvoice) -> Tuple[bool, str]:
        """
        Evaluates Input Tax Credit (ITC) eligibility under Section 16 & Section 17(5) CGST Act.
        Returns (is_eligible, reason).
        """
        # 1. Basic eligibility requirements
        if not invoice.buyer_gstin:
            return (False, "ITC Ineligible: Buyer GSTIN is missing. Recipient must be GST registered to claim ITC.")

        if not invoice.vendor_gstin:
            return (False, "ITC Ineligible: Supplier GSTIN is missing. Input credit cannot be claimed without supplier tax ID.")

        # 2. Statutory Blocked Credits check (Section 17(5))
        for item in invoice.line_items:
            desc_lower = item.description.lower()
            if any(blocked in desc_lower for blocked in AccountingPolicy.BLOCKED_ITC_KEYWORDS):
                return (
                    False,
                    f"ITC Blocked under Section 17(5) CGST Act: Item '{item.description}' matches statutory blocked categories."
                )

        return (True, "Eligible for Input Tax Credit under Section 16 CGST Act (Valid B2B Tax Invoice).")

    @classmethod
    def interpret_invoice(
        cls,
        invoice: ExtractedInvoice,
        document_id: str = "doc_simulated",
        creditor_account_code: str = "2010",
        business_type: str = "IT_SERVICES",
        invoice_direction: str = "PURCHASE"
    ) -> ProposedJournalEntry:
        """
        Interprets an ExtractedInvoice and constructs a balanced ProposedJournalEntry
        with full audit explanations and GST tax treatment for both PURCHASE (Inward)
        and SALES (Outward) transactions, aware of entity commercial profile.
        """
        lines: List[ProposedJournalLine] = []
        applied_rules: List[str] = []
        review_reasons: List[str] = []
        requires_review = False
        fy = get_financial_year(invoice.invoice_date)

        # ==============================================================
        # BRANCH A: SALES / OUTWARD SUPPLY (Revenue, Output Tax, AR)
        # ==============================================================
        if invoice_direction.upper() == "SALES":
            applied_rules.append("Transaction Direction: Outward Tax Invoice (Sales & Service Revenue)")

            # 1. Credit Sales & Service Revenue
            lines.append(
                ProposedJournalLine(
                    account_code="4010",
                    account_name="Sales & Service Revenue",
                    entry_type=EntryType.CREDIT,
                    amount=invoice.subtotal.quantize(Decimal("0.01")),
                    description=f"Revenue from sales to {invoice.buyer_name or 'Customer'}"
                )
            )

            # 2. Credit Output GST
            seller_state = invoice.vendor_gstin[:2] if invoice.vendor_gstin and len(invoice.vendor_gstin) >= 2 else "07"
            buyer_state = ""
            if invoice.place_of_supply_state_code:
                buyer_state = invoice.place_of_supply_state_code
            elif invoice.place_of_supply:
                match = re.search(r"\b(\d{2})\b", invoice.place_of_supply)
                if match:
                    buyer_state = match.group(1)
            elif invoice.buyer_gstin and len(invoice.buyer_gstin) >= 2:
                buyer_state = invoice.buyer_gstin[:2]

            is_intra = (seller_state == buyer_state) if (seller_state and buyer_state) else True

            if invoice.total_tax > Decimal("0.00"):
                if not is_intra:
                    applied_rules.append(f"Inter-state Sales Supply: Output IGST applied ({seller_state} -> {buyer_state}).")
                    lines.append(
                        ProposedJournalLine(
                            account_code="2083",
                            account_name="Output IGST A/c",
                            entry_type=EntryType.CREDIT,
                            amount=invoice.total_tax.quantize(Decimal("0.01")),
                            description="Output IGST collected on inter-state sales"
                        )
                    )
                else:
                    applied_rules.append(f"Intra-state Sales Supply: Output CGST + SGST applied (State {seller_state}).")
                    cgst_amt = (invoice.total_tax / Decimal("2.00")).quantize(Decimal("0.01"))
                    sgst_amt = invoice.total_tax - cgst_amt
                    lines.append(
                        ProposedJournalLine(
                            account_code="2081",
                            account_name="Output CGST A/c",
                            entry_type=EntryType.CREDIT,
                            amount=cgst_amt,
                            description="Output CGST collected on intra-state sales"
                        )
                    )
                    lines.append(
                        ProposedJournalLine(
                            account_code="2082",
                            account_name="Output SGST A/c",
                            entry_type=EntryType.CREDIT,
                            amount=sgst_amt,
                            description="Output SGST collected on intra-state sales"
                        )
                    )

            # 3. Round-off adjustment on sales
            if invoice.round_off != Decimal("0.00"):
                if invoice.round_off > Decimal("0.00"):
                    lines.append(ProposedJournalLine(
                        account_code="5090",
                        account_name="Rounding Off & Fractional Variance",
                        entry_type=EntryType.CREDIT,
                        amount=invoice.round_off,
                        description="Round-off addition credit on sales invoice"
                    ))
                else:
                    lines.append(ProposedJournalLine(
                        account_code="5090",
                        account_name="Rounding Off & Fractional Variance",
                        entry_type=EntryType.DEBIT,
                        amount=abs(invoice.round_off),
                        description="Round-off concession debit on sales invoice"
                    ))

            # 4. Debit Accounts Receivable or Cash/Bank
            customer_name = invoice.buyer_name or "Trade Debtor"
            if invoice.is_settled_or_paid or (invoice.payment_terms and "cash" in invoice.payment_terms.lower()):
                applied_rules.append("Immediate cash/bank receipt for sales invoice")
                lines.append(
                    ProposedJournalLine(
                        account_code="1020",
                        account_name="Current Bank Account",
                        entry_type=EntryType.DEBIT,
                        amount=invoice.grand_total.quantize(Decimal("0.01")),
                        description=f"Immediate settlement for sales invoice #{invoice.invoice_number}"
                    )
                )
                tx_type = TransactionType.SALES_REVENUE
            else:
                applied_rules.append(f"Credit Sales: Debited Accounts Receivable - {customer_name}")
                lines.append(
                    ProposedJournalLine(
                        account_code="1030",
                        account_name=f"Accounts Receivable - {customer_name}",
                        entry_type=EntryType.DEBIT,
                        amount=invoice.grand_total.quantize(Decimal("0.01")),
                        description=f"Trade receivable from {customer_name} for invoice #{invoice.invoice_number}"
                    )
                )
                tx_type = TransactionType.SALES_CREDIT

            narration = f"Being sales of goods/services to {customer_name} vide tax invoice #{invoice.invoice_number} dated {invoice.invoice_date}"

            return ProposedJournalEntry(
                source_document_id=document_id,
                invoice_number=invoice.invoice_number,
                entry_date=invoice.invoice_date,
                financial_year=fy,
                invoice_type="SALES",
                transaction_type=tx_type,
                narration=narration,
                lines=lines,
                reasoning=f"Outward Sales transaction generated under Indian GST rules for {fy}.",
                applied_rules=applied_rules,
                requires_human_review=requires_review,
                review_reasons=review_reasons,
                itc_recoverable=False,
                supplier_gstin=invoice.vendor_gstin,
                place_of_supply=invoice.place_of_supply or buyer_state
            )

        # ==============================================================
        # BRANCH B: PURCHASE / INWARD SUPPLY (Expense/Asset, Input Tax, AP)
        # ==============================================================
        # 1. Classify each line item using entity commercial profile
        account_allocations: Dict[Tuple[str, str], Decimal] = {}

        for item in invoice.line_items:
            acc_code, acc_name, acc_cat, explanation, item_needs_review = cls.classify_line_item(
                item, business_type=business_type
            )
            key = (acc_code, acc_name)
            
            # The taxable cost of the line
            line_cost = (item.quantity * item.unit_price) - item.discount_amount
            if line_cost <= Decimal("0.00"):
                line_cost = item.total_amount

            account_allocations[key] = account_allocations.get(key, Decimal("0.00")) + line_cost
            applied_rules.append(explanation)

            if item_needs_review:
                requires_review = True
                review_reasons.append(f"Review required for item '{item.description}': {explanation}")

        # Fallback if no line items
        if not account_allocations:
            default_acc = "5005" if business_type in ("RETAIL_STATIONERY", "FURNITURE_RETAILER") else "5010"
            default_name = "Purchases of Trading Goods / COGS" if default_acc == "5005" else "Office Supplies & Stationery"
            account_allocations[(default_acc, default_name)] = invoice.subtotal
            requires_review = True
            review_reasons.append("No individual line items parsed; allocated subtotal to general expense/purchases pending review.")

        # Create Debit lines for base purchases
        for (code, name), amt in account_allocations.items():
            if amt <= Decimal("0.00"):
                continue
            lines.append(
                ProposedJournalLine(
                    account_code=code,
                    account_name=name,
                    entry_type=EntryType.DEBIT,
                    amount=amt.quantize(Decimal("0.01")),
                    description=f"Taxable value for {name}"
                )
            )

        # 2. Evaluate GST & Input Tax Credit
        itc_eligible, itc_reason = cls.evaluate_itc_eligibility(invoice)
        applied_rules.append(itc_reason)

        if not itc_eligible:
            requires_review = True
            review_reasons.append(itc_reason)

        # Determine Place of Supply and Supply Type (Intra vs Inter state)
        supplier_state = invoice.vendor_gstin[:2] if invoice.vendor_gstin and len(invoice.vendor_gstin) >= 2 else ""
        
        pos_state = ""
        if invoice.place_of_supply_state_code:
            pos_state = invoice.place_of_supply_state_code
        elif invoice.place_of_supply:
            match = re.search(r"\b(\d{2})\b", invoice.place_of_supply)
            if match:
                pos_state = match.group(1)
        elif invoice.buyer_gstin and len(invoice.buyer_gstin) >= 2:
            pos_state = invoice.buyer_gstin[:2]

        is_intra_state = (supplier_state == pos_state) if (supplier_state and pos_state) else True

        # Post Tax lines
        if invoice.total_tax > Decimal("0.00"):
            if not itc_eligible:
                # Ineligible GST expensed or capitalized
                applied_rules.append("Non-recoverable GST debited to Ineligible GST Expense (Code 5080)")
                lines.append(
                    ProposedJournalLine(
                        account_code="5080",
                        account_name="Ineligible Input GST Expense",
                        entry_type=EntryType.DEBIT,
                        amount=invoice.total_tax,
                        description="Ineligible Input GST (Section 17(5) / unregistered)"
                    )
                )
            elif not is_intra_state:
                # Inter-state: IGST
                applied_rules.append(f"Inter-state supply: Supplier State ({supplier_state}) != POS ({pos_state}). Input IGST applied.")
                lines.append(
                    ProposedJournalLine(
                        account_code="1083",
                        account_name="Input IGST A/c",
                        entry_type=EntryType.DEBIT,
                        amount=invoice.total_tax,
                        description="Input IGST on inter-state taxable supply"
                    )
                )
            else:
                # Intra-state: CGST + SGST (separated using actual invoice amounts if present, else equal split)
                applied_rules.append(f"Intra-state supply: Supplier State ({supplier_state}) == POS ({pos_state}). Input CGST and SGST applied.")
                cgst_amt = Decimal("0.00")
                sgst_amt = Decimal("0.00")

                for t in invoice.taxes:
                    if t.tax_type.upper() == "CGST":
                        cgst_amt += t.tax_amount
                    elif t.tax_type.upper() == "SGST":
                        sgst_amt += t.tax_amount

                if cgst_amt == Decimal("0.00") or sgst_amt == Decimal("0.00"):
                    cgst_amt = (invoice.total_tax / Decimal("2.00")).quantize(Decimal("0.01"))
                    sgst_amt = invoice.total_tax - cgst_amt

                lines.append(
                    ProposedJournalLine(
                        account_code="1081",
                        account_name="Input CGST A/c",
                        entry_type=EntryType.DEBIT,
                        amount=cgst_amt,
                        description="Input CGST on intra-state supply"
                    )
                )
                lines.append(
                    ProposedJournalLine(
                        account_code="1082",
                        account_name="Input SGST A/c",
                        entry_type=EntryType.DEBIT,
                        amount=sgst_amt,
                        description="Input SGST on intra-state supply"
                    )
                )

        # 3. Round-off adjustment if applicable
        if invoice.round_off != Decimal("0.00"):
            if invoice.round_off > Decimal("0.00"):
                # Positive round off is an expense/cost adjustment
                lines.append(ProposedJournalLine(
                    account_code="5090",
                    account_name="Rounding Off & Fractional Variance",
                    entry_type=EntryType.DEBIT,
                    amount=invoice.round_off,
                    description="Round-off fraction adjustment debit"
                ))
            else:
                # Negative round off reduces payable / credit adjustment
                lines.append(ProposedJournalLine(
                    account_code="5090",
                    account_name="Rounding Off & Fractional Variance",
                    entry_type=EntryType.CREDIT,
                    amount=abs(invoice.round_off),
                    description="Round-off discount/fraction credit"
                ))

        # 4. Credit Accounts Payable or Cash
        if invoice.is_settled_or_paid or (invoice.payment_terms and "cash" in invoice.payment_terms.lower()):
            applied_rules.append("Payment settled: credited Cash in Hand (Code 1010)")
            lines.append(
                ProposedJournalLine(
                    account_code="1010",
                    account_name="Cash in Hand",
                    entry_type=EntryType.CREDIT,
                    amount=invoice.grand_total,
                    description=f"Immediate cash settlement for invoice #{invoice.invoice_number}"
                )
            )
            tx_type = TransactionType.EXPENSE_OFFICE_CASH
        else:
            applied_rules.append(f"Credit purchase: credited Accounts Payable for supplier '{invoice.vendor_name}' (Code {creditor_account_code})")
            lines.append(
                ProposedJournalLine(
                    account_code=creditor_account_code,
                    account_name=f"Accounts Payable - {invoice.vendor_name}",
                    entry_type=EntryType.CREDIT,
                    amount=invoice.grand_total,
                    description=f"Trade liability to {invoice.vendor_name} for invoice #{invoice.invoice_number}"
                )
            )
            is_capital = any(l.account_code in ("1050", "1060", "1070") for l in lines)
            tx_type = TransactionType.ASSET_ACQUISITION_CREDIT if is_capital else TransactionType.PURCHASE_GOODS_CREDIT

        # 5. Check for any validation flags or debit/credit imbalance
        if invoice.validation_flags:
            requires_review = True
            review_reasons.extend(invoice.validation_flags)

        total_deb = sum((l.amount for l in lines if l.entry_type == EntryType.DEBIT), start=Decimal("0.00"))
        total_cred = sum((l.amount for l in lines if l.entry_type == EntryType.CREDIT), start=Decimal("0.00"))
        
        if total_deb != total_cred:
            requires_review = True
            review_reasons.append(f"Imbalance between Debits ({total_deb}) and Credits ({total_cred})")

        narration = f"Being purchase of goods/services from {invoice.vendor_name} vide invoice #{invoice.invoice_number} dated {invoice.invoice_date}"

        return ProposedJournalEntry(
            source_document_id=document_id,
            invoice_number=invoice.invoice_number,
            entry_date=invoice.invoice_date,
            financial_year=fy,
            invoice_type="PURCHASE",
            transaction_type=tx_type,
            narration=narration,
            lines=lines,
            reasoning=f"Deterministic accounting interpretation based on item description, HSN classification, and Indian GST rules for {fy}.",
            applied_rules=applied_rules,
            requires_human_review=requires_review,
            review_reasons=review_reasons,
            itc_recoverable=itc_eligible,
            supplier_gstin=invoice.vendor_gstin,
            place_of_supply=invoice.place_of_supply or pos_state
        )
