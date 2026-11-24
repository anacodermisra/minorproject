import re
from decimal import Decimal
from typing import List, Set, Tuple, Optional, Dict
from app.schemas.accounting import (
    ProposedJournalEntry,
    EntryType,
    ValidationCheckStatus,
    ValidationCheckResult,
    DocumentValidationReport,
)
from app.schemas.invoice import ExtractedInvoice, InvoiceLineItem


class InvariantViolation(Exception):
    """Raised when a non-negotiable accounting or mathematical rule is broken."""
    pass


class DuplicateInvoiceViolation(InvariantViolation):
    """Raised when an invoice has already been posted for this supplier."""
    pass


def validate_double_entry_invariants(entry: ProposedJournalEntry) -> Tuple[bool, List[str]]:
    """Legacy helper returning boolean and error strings."""
    report = validate_journal_invariants_detailed(entry)
    errors = [c.explanation for c in report if c.status == ValidationCheckStatus.FAIL]
    return (len(errors) == 0, errors)


def validate_chart_of_accounts(entry: ProposedJournalEntry, active_account_codes: Set[str]) -> Tuple[bool, List[str]]:
    """Validates that every referenced account exists and is active in the company's Chart of Accounts."""
    errors: List[str] = []
    for line in entry.lines:
        if line.account_code not in active_account_codes:
            errors.append(
                f"Account '{line.account_name}' with code '{line.account_code}' does not exist or is inactive in Chart of Accounts."
            )
    return (len(errors) == 0, errors)


def validate_invoice_arithmetic(invoice: ExtractedInvoice, tolerance: Decimal = Decimal("0.05")) -> Tuple[bool, List[str]]:
    """
    Validates arithmetic consistency across invoice line items and totals.
    Legacy/convenience wrapper returning (is_valid, warnings).
    """
    warnings: List[str] = []

    # 1. Line item math checks
    for idx, item in enumerate(invoice.line_items, 1):
        disc = getattr(item, "discount_amount", getattr(item, "discount", Decimal("0.00")))
        expected_gross = (item.quantity * item.unit_price) - disc
        if abs(item.total_amount - expected_gross) > tolerance:
            warnings.append(
                f"Line item {idx} ('{item.description}'): Math mismatch. "
                f"Qty ({item.quantity}) * Unit Price ({item.unit_price}) - Disc ({disc}) = {expected_gross}, "
                f"but extracted line total is {item.total_amount}"
            )

    # 2. Subtotal check
    sum_lines = sum((item.total_amount for item in invoice.line_items), Decimal("0.00"))
    diff_sub_direct = abs(sum_lines - invoice.subtotal)
    diff_sub_discount = abs((sum_lines + invoice.total_discount) - invoice.subtotal)
    diff_sub_net = abs(sum_lines - (invoice.subtotal - invoice.total_discount))
    if diff_sub_direct > tolerance and diff_sub_discount > tolerance and diff_sub_net > tolerance:
        warnings.append(
            f"Subtotal discrepancy: Sum of line items ({sum_lines}) != invoice subtotal ({invoice.subtotal})"
        )

    # 3. Grand total check
    diff_net = abs((invoice.subtotal + invoice.total_tax + invoice.round_off) - invoice.grand_total)
    diff_gross = abs((invoice.subtotal + invoice.total_tax - invoice.total_discount + invoice.round_off) - invoice.grand_total)
    if diff_net > tolerance and diff_gross > tolerance:
        expected_calc = invoice.subtotal + invoice.total_tax + invoice.round_off
        warnings.append(
            f"Grand total discrepancy: Subtotal ({invoice.subtotal}) + Tax ({invoice.total_tax}) + Round-off ({invoice.round_off}) = {expected_calc}, "
            f"but extracted grand total is {invoice.grand_total}"
        )

    is_valid = len(warnings) == 0
    return (is_valid, warnings)


def validate_line_item_math(item: InvoiceLineItem, idx: int = 1, tolerance: Decimal = Decimal("0.05")) -> List[ValidationCheckResult]:
    """
    Validates arithmetic and non-negativity for a single invoice line item:
    Gross = Quantity * Unit Rate.
    Taxable = Gross - Discount.
    Line Total = Taxable (or Tax-inclusive Total).
    """
    results: List[ValidationCheckResult] = []

    # 1. Non-negativity checks
    if item.quantity <= Decimal("0.00"):
        results.append(ValidationCheckResult(
            check_name=f"Line {idx} Quantity Check",
            status=ValidationCheckStatus.FAIL,
            expected_value="> 0.00",
            actual_value=str(item.quantity),
            explanation=f"Line {idx} ('{item.description}'): Quantity must be strictly positive.",
            source_fields=["quantity"],
            requires_human_review=True
        ))

    if item.unit_price < Decimal("0.00"):
        results.append(ValidationCheckResult(
            check_name=f"Line {idx} Unit Price Check",
            status=ValidationCheckStatus.FAIL,
            expected_value=">= 0.00",
            actual_value=str(item.unit_price),
            explanation=f"Line {idx} ('{item.description}'): Unit price cannot be negative.",
            source_fields=["unit_price"],
            requires_human_review=True
        ))

    # 2. Arithmetic: Gross - Discount
    gross = (item.quantity * item.unit_price).quantize(Decimal("0.01"))
    expected_taxable = gross - item.discount_amount

    # If line total matches expected taxable (or tax-inclusive taxable + tax)
    diff_taxable = abs(expected_taxable - item.total_amount)
    
    # Check if total_amount is tax-inclusive: taxable + tax_amount
    expected_with_tax = expected_taxable + item.tax_amount
    diff_with_tax = abs(expected_with_tax - item.total_amount)

    is_math_correct = (diff_taxable <= tolerance) or (diff_with_tax <= tolerance)
    
    if not is_math_correct:
        results.append(ValidationCheckResult(
            check_name=f"Line {idx} Arithmetic Reconciliation",
            status=ValidationCheckStatus.FAIL,
            expected_value=f"Taxable: {expected_taxable} (or with Tax: {expected_with_tax})",
            actual_value=str(item.total_amount),
            difference=str(min(diff_taxable, diff_with_tax)),
            explanation=f"Line {idx} ('{item.description}'): Qty ({item.quantity}) * Rate ({item.unit_price}) - Disc ({item.discount_amount}) = {expected_taxable}, but extracted total is {item.total_amount}.",
            source_fields=["quantity", "unit_price", "discount_amount", "total_amount"],
            requires_human_review=True
        ))
    else:
        results.append(ValidationCheckResult(
            check_name=f"Line {idx} Arithmetic Reconciliation",
            status=ValidationCheckStatus.PASS,
            expected_value=str(item.total_amount),
            actual_value=str(item.total_amount),
            explanation=f"Line {idx} arithmetic verified successfully.",
            source_fields=["quantity", "unit_price", "discount_amount", "total_amount"]
        ))

    return results


def validate_invoice_reconciliation(invoice: ExtractedInvoice, tolerance: Decimal = Decimal("0.05")) -> List[ValidationCheckResult]:
    """
    Validates document-level arithmetic reconciliations:
    - Line items exist and do not contain footer / summary rows.
    - Sum of line items == Subtotal.
    - Subtotal + Total Tax - Total Discount + Round Off == Grand Total.
    - Sum of tax components == Total Tax.
    """
    results: List[ValidationCheckResult] = []

    # 1. Line items presence
    if not invoice.line_items:
        results.append(ValidationCheckResult(
            check_name="Line Items Presence",
            status=ValidationCheckStatus.WARNING,
            expected_value=">= 1 line items",
            actual_value="0 items",
            explanation="No individual product line items extracted. Verify if invoice is summary-only.",
            source_fields=["line_items"],
            requires_human_review=True
        ))

    # 2. Check for summary / footer rows accidentally treated as line items
    summary_keywords = ["subtotal", "sub total", "total tax", "cgst", "sgst", "igst", "round off", "grand total", "bank / payment", "neft reference", "declaration"]
    for idx, item in enumerate(invoice.line_items):
        desc_lower = item.description.lower()
        if any(kw in desc_lower for kw in summary_keywords):
            results.append(ValidationCheckResult(
                check_name=f"Summary Row Contamination Check (Line {idx+1})",
                status=ValidationCheckStatus.FAIL,
                expected_value="Product or service description",
                actual_value=item.description,
                explanation=f"Summary/footer text '{item.description}' was incorrectly captured as a product line item.",
                source_fields=["line_items"],
                requires_human_review=True
            ))

    # 3. Sum of line items vs Subtotal
    if invoice.line_items:
        sum_lines = sum((item.total_amount for item in invoice.line_items), start=Decimal("0.00")).quantize(Decimal("0.01"))
        # Line totals might be taxable or tax-inclusive; compare against subtotal or grand_total
        diff_subtotal = abs(sum_lines - invoice.subtotal)
        diff_sub_discount = abs((sum_lines + invoice.total_discount) - invoice.subtotal)
        diff_sub_net = abs(sum_lines - (invoice.subtotal - invoice.total_discount))
        diff_grand = abs(sum_lines - invoice.grand_total)

        if (
            diff_subtotal > tolerance
            and diff_sub_discount > tolerance
            and diff_sub_net > tolerance
            and diff_grand > tolerance
        ):
            results.append(ValidationCheckResult(
                check_name="Subtotal Reconciliation",
                status=ValidationCheckStatus.FAIL,
                expected_value=str(invoice.subtotal),
                actual_value=str(sum_lines),
                difference=str(diff_subtotal),
                explanation=f"Sum of line items ({sum_lines}) does not match extracted taxable subtotal ({invoice.subtotal}).",
                source_fields=["line_items", "subtotal"],
                requires_human_review=True
            ))
        else:
            results.append(ValidationCheckResult(
                check_name="Subtotal Reconciliation",
                status=ValidationCheckStatus.PASS,
                expected_value=str(invoice.subtotal),
                actual_value=str(invoice.subtotal),
                explanation="Sum of line items agrees with extracted subtotal.",
                source_fields=["line_items", "subtotal"]
            ))

    # 4. Grand Total Reconciliation:
    # Option A: Subtotal is already net of line discounts: Subtotal + Total Tax + Round Off == Grand Total
    expected_grand_net = (invoice.subtotal + invoice.total_tax + invoice.round_off).quantize(Decimal("0.01"))
    diff_net = abs(expected_grand_net - invoice.grand_total)

    # Option B: Total Discount is deducted at invoice level: Subtotal + Total Tax - Total Discount + Round Off == Grand Total
    expected_grand_gross = (invoice.subtotal + invoice.total_tax - invoice.total_discount + invoice.round_off).quantize(Decimal("0.01"))
    diff_gross = abs(expected_grand_gross - invoice.grand_total)

    if diff_net <= tolerance:
        results.append(ValidationCheckResult(
            check_name="Grand Total Reconciliation",
            status=ValidationCheckStatus.PASS,
            expected_value=str(expected_grand_net),
            actual_value=str(invoice.grand_total),
            explanation="Grand total perfectly reconciles with subtotal, taxes, and round-off.",
            source_fields=["subtotal", "total_tax", "round_off", "grand_total"]
        ))
    elif diff_gross <= tolerance:
        results.append(ValidationCheckResult(
            check_name="Grand Total Reconciliation",
            status=ValidationCheckStatus.PASS,
            expected_value=str(expected_grand_gross),
            actual_value=str(invoice.grand_total),
            explanation="Grand total perfectly reconciles with subtotal, taxes, invoice discount, and round-off.",
            source_fields=["subtotal", "total_tax", "total_discount", "round_off", "grand_total"]
        ))
    else:
        results.append(ValidationCheckResult(
            check_name="Grand Total Reconciliation",
            status=ValidationCheckStatus.FAIL,
            expected_value=f"{expected_grand_net} (or {expected_grand_gross} with summary discount)",
            actual_value=str(invoice.grand_total),
            difference=str(min(diff_net, diff_gross)),
            explanation=f"Grand total discrepancy: Subtotal ({invoice.subtotal}) + Tax ({invoice.total_tax}) + RoundOff ({invoice.round_off}) = {expected_grand_net}, but extracted grand total is {invoice.grand_total}.",
            source_fields=["subtotal", "total_tax", "total_discount", "round_off", "grand_total"],
            requires_human_review=True
        ))

    # 5. Tax Components Sum check (if tax breakup items exist)
    if invoice.taxes:
        sum_tax_components = sum((t.tax_amount for t in invoice.taxes), start=Decimal("0.00")).quantize(Decimal("0.01"))
        diff_tax = abs(sum_tax_components - invoice.total_tax)
        if diff_tax > tolerance:
            results.append(ValidationCheckResult(
                check_name="Tax Component Breakdown Reconciliation",
                status=ValidationCheckStatus.FAIL,
                expected_value=str(invoice.total_tax),
                actual_value=str(sum_tax_components),
                difference=str(diff_tax),
                explanation=f"Sum of tax breakup components ({sum_tax_components}) does not match declared total tax ({invoice.total_tax}).",
                source_fields=["taxes", "total_tax"],
                requires_human_review=True
            ))

    return results


def validate_gst_treatment(invoice: ExtractedInvoice) -> List[ValidationCheckResult]:
    """
    Validates consistency of GST tax components against Place of Supply (POS)
    and supplier location according to Indian GST law:
    - Intra-state (Supplier State == POS State): Must apply CGST and SGST.
    - Inter-state (Supplier State != POS State): Must apply IGST.
    """
    results: List[ValidationCheckResult] = []

    if not invoice.vendor_gstin:
        results.append(ValidationCheckResult(
            check_name="Supplier GSTIN Validation",
            status=ValidationCheckStatus.WARNING,
            explanation="Supplier GSTIN is missing. Tax treatment and ITC eligibility cannot be verified automatically.",
            source_fields=["vendor_gstin"],
            requires_human_review=True
        ))
        return results

    supplier_state = invoice.vendor_gstin[:2] if len(invoice.vendor_gstin) >= 2 else ""

    # Determine Place of Supply state code
    pos_state = ""
    if invoice.place_of_supply_state_code:
        pos_state = invoice.place_of_supply_state_code
    elif invoice.place_of_supply:
        match = re.search(r"\b(\d{2})\b", invoice.place_of_supply)
        if match:
            pos_state = match.group(1)
    elif invoice.buyer_gstin and len(invoice.buyer_gstin) >= 2:
        pos_state = invoice.buyer_gstin[:2]

    if not pos_state or not supplier_state:
        results.append(ValidationCheckResult(
            check_name="Place of Supply Determination",
            status=ValidationCheckStatus.WARNING,
            explanation="Place of supply state code could not be determined with certainty. Human review required.",
            source_fields=["place_of_supply", "vendor_gstin", "buyer_gstin"],
            requires_human_review=True
        ))
        return results

    is_intra_state = (supplier_state == pos_state)
    expected_tax_type = "Intra-state (CGST + SGST)" if is_intra_state else "Inter-state (IGST)"

    # Check extracted tax components if available
    tax_types_present = {t.tax_type.upper() for t in invoice.taxes}
    
    if is_intra_state:
        if "IGST" in tax_types_present and not ("CGST" in tax_types_present or "SGST" in tax_types_present):
            results.append(ValidationCheckResult(
                check_name="GST Supply Type & Component Consistency",
                status=ValidationCheckStatus.FAIL,
                expected_value="CGST + SGST (Intra-state: Supplier state matches POS)",
                actual_value="IGST applied",
                explanation=f"Supplier State ({supplier_state}) equals Place of Supply ({pos_state}), which constitutes an intra-state supply, but invoice applies IGST.",
                source_fields=["vendor_gstin", "place_of_supply", "taxes"],
                requires_human_review=True
            ))
        else:
            results.append(ValidationCheckResult(
                check_name="GST Supply Type & Component Consistency",
                status=ValidationCheckStatus.PASS,
                expected_value=expected_tax_type,
                actual_value=expected_tax_type,
                explanation=f"Intra-state supply verified (Supplier State {supplier_state} == POS {pos_state}).",
                source_fields=["vendor_gstin", "place_of_supply"]
            ))
    else:
        if ("CGST" in tax_types_present or "SGST" in tax_types_present) and "IGST" not in tax_types_present:
            results.append(ValidationCheckResult(
                check_name="GST Supply Type & Component Consistency",
                status=ValidationCheckStatus.FAIL,
                expected_value="IGST (Inter-state: Supplier state differs from POS)",
                actual_value="CGST + SGST applied",
                explanation=f"Supplier State ({supplier_state}) differs from Place of Supply ({pos_state}), which constitutes an inter-state supply, but invoice applies CGST/SGST.",
                source_fields=["vendor_gstin", "place_of_supply", "taxes"],
                requires_human_review=True
            ))
        else:
            results.append(ValidationCheckResult(
                check_name="GST Supply Type & Component Consistency",
                status=ValidationCheckStatus.PASS,
                expected_value=expected_tax_type,
                actual_value=expected_tax_type,
                explanation=f"Inter-state supply verified (Supplier State {supplier_state} != POS {pos_state}).",
                source_fields=["vendor_gstin", "place_of_supply"]
            ))

    return results


def validate_journal_invariants_detailed(
    entry: ProposedJournalEntry,
    invoice: Optional[ExtractedInvoice] = None,
    active_account_codes: Optional[Set[str]] = None
) -> List[ValidationCheckResult]:
    """
    Validates structural and accounting invariants on a proposed double-entry journal:
    1. Line count >= 2.
    2. At least one Debit and at least one Credit.
    3. All amounts strictly positive.
    4. Total Debits == Total Credits (Exact Decimal equality).
    5. All account codes exist in active Chart of Accounts.
    6. Reconciles journal payable liability against invoice grand total.
    """
    results: List[ValidationCheckResult] = []

    # 1. Line count
    if len(entry.lines) < 2:
        results.append(ValidationCheckResult(
            check_name="Journal Line Count",
            status=ValidationCheckStatus.FAIL,
            expected_value=">= 2 lines",
            actual_value=f"{len(entry.lines)} lines",
            explanation="A journal entry must contain at least 2 lines (at least one Debit and one Credit).",
            requires_human_review=True
        ))

    # 2. Debit & Credit presence
    has_debit = any(l.entry_type == EntryType.DEBIT for l in entry.lines)
    has_credit = any(l.entry_type == EntryType.CREDIT for l in entry.lines)
    if not has_debit or not has_credit:
        results.append(ValidationCheckResult(
            check_name="Debit and Credit Representation",
            status=ValidationCheckStatus.FAIL,
            expected_value="Both Debit and Credit present",
            actual_value=f"Debit: {has_debit}, Credit: {has_credit}",
            explanation="A journal entry must contain both Debit and Credit allocations.",
            requires_human_review=True
        ))

    # 3. Positive amounts
    for idx, line in enumerate(entry.lines):
        if line.amount <= Decimal("0.00"):
            results.append(ValidationCheckResult(
                check_name=f"Line {idx+1} Non-negative Monetary Amount",
                status=ValidationCheckStatus.FAIL,
                expected_value="> 0.00",
                actual_value=str(line.amount),
                explanation=f"Line {idx+1} ({line.account_name}): Monetary amount must be strictly positive.",
                requires_human_review=True
            ))

    # 4. Debits == Credits Equality (Core Invariant)
    total_debits = entry.total_debits
    total_credits = entry.total_credits
    if total_debits != total_credits:
        results.append(ValidationCheckResult(
            check_name="Double-Entry Balance Invariant",
            status=ValidationCheckStatus.FAIL,
            expected_value=f"Debits == Credits ({total_debits})",
            actual_value=f"Debits: {total_debits}, Credits: {total_credits}",
            difference=str(abs(total_debits - total_credits)),
            explanation=f"Double-entry imbalance detected: Total Debits ({total_debits}) != Total Credits ({total_credits}).",
            requires_human_review=True
        ))
    else:
        results.append(ValidationCheckResult(
            check_name="Double-Entry Balance Invariant",
            status=ValidationCheckStatus.PASS,
            expected_value=str(total_debits),
            actual_value=str(total_credits),
            explanation=f"Total Debits ({total_debits}) equal Total Credits ({total_credits}) with exact decimal precision.",
        ))

    # 5. Chart of Accounts validity
    if active_account_codes is not None:
        for idx, line in enumerate(entry.lines):
            if line.account_code not in active_account_codes:
                results.append(ValidationCheckResult(
                    check_name=f"Chart of Accounts Verification (Line {idx+1})",
                    status=ValidationCheckStatus.FAIL,
                    expected_value="Active code in Chart of Accounts",
                    actual_value=f"{line.account_code} ({line.account_name})",
                    explanation=f"Account '{line.account_name}' with code '{line.account_code}' does not exist or is inactive.",
                    requires_human_review=True
                ))

    # 6. Reconcile Journal Payable/Receivable against Source Invoice Grand Total
    # A journal can balance at 60,000 when invoice was 50,000! We must reconcile against source doc.
    if invoice is not None:
        is_sales = getattr(entry, "invoice_type", "PURCHASE") == "SALES"
        if is_sales:
            claim_lines = [l for l in entry.lines if l.entry_type == EntryType.DEBIT and l.account_code in ("1030", "1020", "1010")]
            total_claim = sum((l.amount for l in claim_lines), start=Decimal("0.00")).quantize(Decimal("0.01"))
            diff_invoice = abs(total_claim - invoice.grand_total)
            label = "Receivable asset"
        else:
            claim_lines = [l for l in entry.lines if l.entry_type == EntryType.CREDIT and l.account_code in ("2010", "1010", "1020")]
            total_claim = sum((l.amount for l in claim_lines), start=Decimal("0.00")).quantize(Decimal("0.01"))
            diff_invoice = abs(total_claim - invoice.grand_total)
            label = "Payable liability"
        
        check_title = "Source Invoice Receivable Reconciliation" if is_sales else "Source Invoice Payable Reconciliation"
        if diff_invoice > Decimal("0.05"):
            results.append(ValidationCheckResult(
                check_name=check_title,
                status=ValidationCheckStatus.FAIL,
                expected_value=str(invoice.grand_total),
                actual_value=str(total_claim),
                difference=str(diff_invoice),
                explanation=f"Journal {label} ({total_claim}) does not match source invoice grand total ({invoice.grand_total}).",
                requires_human_review=True
            ))
        else:
            results.append(ValidationCheckResult(
                check_name=check_title,
                status=ValidationCheckStatus.PASS,
                expected_value=str(invoice.grand_total),
                actual_value=str(total_claim),
                explanation=f"Journal {label} reconciles with source invoice grand total."
            ))

    return results


def run_comprehensive_validation(
    invoice: ExtractedInvoice,
    entry: ProposedJournalEntry,
    active_account_codes: Optional[Set[str]] = None,
    is_duplicate: bool = False
) -> DocumentValidationReport:
    """
    Executes the entire multi-stage validation suite:
    1. Line-item arithmetic & non-negativity.
    2. Document-level reconciliation & footer check.
    3. GST tax treatment consistency.
    4. Journal structural invariants (Debits == Credits).
    5. Chart of Accounts verification.
    6. Payable-to-invoice reconciliation.
    7. Duplicate posting gate.
    """
    all_checks: List[ValidationCheckResult] = []

    # 1. Line item checks
    for idx, item in enumerate(invoice.line_items):
        all_checks.extend(validate_line_item_math(item, idx=idx+1))

    # 2. Document reconciliations
    all_checks.extend(validate_invoice_reconciliation(invoice))

    # 3. GST tax treatment consistency
    all_checks.extend(validate_gst_treatment(invoice))

    # 4. Journal invariants & COA & source reconciliation
    all_checks.extend(validate_journal_invariants_detailed(
        entry=entry,
        invoice=invoice,
        active_account_codes=active_account_codes
    ))

    # 5. Duplicate posting gate
    if is_duplicate:
        all_checks.append(ValidationCheckResult(
            check_name="Duplicate Invoice Posting Gate",
            status=ValidationCheckStatus.FAIL,
            expected_value="Unique unposted invoice",
            actual_value=f"Invoice #{invoice.invoice_number} already posted",
            explanation=f"Invoice #{invoice.invoice_number} from vendor '{invoice.vendor_name}' has already been posted to the ledger.",
            requires_human_review=True
        ))

    # Determine report status
    has_blocking_failures = any(c.status == ValidationCheckStatus.FAIL for c in all_checks)
    requires_human_review = entry.requires_human_review or any(c.requires_human_review for c in all_checks) or (not has_blocking_failures and any(c.status == ValidationCheckStatus.WARNING for c in all_checks))

    is_valid = not has_blocking_failures
    can_post_automatically = is_valid and not requires_human_review

    if has_blocking_failures:
        failure_count = sum(1 for c in all_checks if c.status == ValidationCheckStatus.FAIL)
        summary = f"Validation blocked: {failure_count} critical invariant check(s) failed."
    elif requires_human_review:
        warning_count = sum(1 for c in all_checks if c.status == ValidationCheckStatus.WARNING)
        summary = f"Validation warning: Review required ({warning_count} checks flagged)."
    else:
        summary = "All document, tax, and accounting invariants verified successfully."

    return DocumentValidationReport(
        is_valid=is_valid,
        can_post_automatically=can_post_automatically,
        has_blocking_failures=has_blocking_failures,
        checks=all_checks,
        summary_message=summary
    )
