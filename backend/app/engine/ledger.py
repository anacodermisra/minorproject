from decimal import Decimal
from datetime import date, datetime, timezone
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.accounting import (
    Tenant,
    Account,
    JournalEntry,
    JournalLine,
    AuditLog,
    EntryPostingStatus,
)
from app.schemas.accounting import (
    ProposedJournalEntry,
    EntryType,
    TransactionType,
    AccountCategory,
    NormalBalance,
    ValidationCheckStatus,
)
from app.schemas.reports import LedgerAccountBalance, TrialBalanceReport
from app.engine.invariants import (
    validate_double_entry_invariants,
    validate_chart_of_accounts,
    validate_journal_invariants_detailed,
    InvariantViolation,
    DuplicateInvoiceViolation,
)
from app.engine.interpreter import get_financial_year


def post_journal_entry(
    db: Session,
    tenant_id: str,
    proposal: ProposedJournalEntry,
    posted_by: str = "SYSTEM_AUTOMATION",
    allow_review_override: bool = False,
    invoice_id: Optional[str] = None
) -> JournalEntry:
    """
    Atomically posts a validated journal entry into the authoritative ledger.
    Enforces:
    1. Duplicate invoice posting prevention.
    2. Zero tolerance for double-entry imbalance.
    3. All referenced accounts exist and are active in the tenant's Chart of Accounts.
    4. Non-negative amounts.
    5. Human approval verification if review is required.
    """
    # 1. Duplicate Invoice Posting Prevention
    existing_entry = (
        db.query(JournalEntry)
        .filter(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.invoice_number == proposal.invoice_number,
            JournalEntry.status == EntryPostingStatus.POSTED
        )
        .first()
    )
    if existing_entry:
        raise DuplicateInvoiceViolation(
            f"Duplicate Posting Blocked: Invoice #{proposal.invoice_number} has already been posted to the ledger (Entry ID: {existing_entry.id})."
        )

    # 2. Detailed Journal Invariants & COA Checks
    tenant_accounts = db.query(Account).filter(Account.tenant_id == tenant_id, Account.is_active == True).all()
    account_code_map = {acc.code: acc for acc in tenant_accounts}
    active_codes = set(account_code_map.keys())

    checks = validate_journal_invariants_detailed(
        entry=proposal,
        active_account_codes=active_codes
    )

    failures = [c.explanation for c in checks if c.status == ValidationCheckStatus.FAIL]
    if failures:
        raise InvariantViolation(f"Cannot post invalid journal entry: {'; '.join(failures)}")

    # 3. Human Approval Gate
    # If the proposal was flagged for review (e.g. ambiguous classification, warnings),
    # an automated system cannot post it without explicit human approval.
    if proposal.requires_human_review and posted_by == "SYSTEM_AUTOMATION" and not allow_review_override:
        raise InvariantViolation(
            f"Posting Gate Blocked: Entry for invoice #{proposal.invoice_number} requires human review: {'; '.join(proposal.review_reasons)}"
        )

    # 4. Atomic Database Transaction: Post Entry and Lines
    try:
        fy = proposal.financial_year or get_financial_year(proposal.entry_date)
        db_entry = JournalEntry(
            tenant_id=tenant_id,
            document_id=proposal.source_document_id if proposal.source_document_id and proposal.source_document_id != "doc_simulated" else None,
            invoice_id=invoice_id,
            invoice_number=proposal.invoice_number,
            entry_date=proposal.entry_date,
            financial_year=fy,
            transaction_type=proposal.transaction_type,
            narration=proposal.narration,
            status=EntryPostingStatus.POSTED,
            posted_at=datetime.now(timezone.utc)
        )
        db.add(db_entry)
        db.flush()  # Generates db_entry.id

        for line in proposal.lines:
            acc = account_code_map[line.account_code]
            db_line = JournalLine(
                entry_id=db_entry.id,
                account_id=acc.id,
                entry_type=line.entry_type,
                amount=line.amount,
                description=line.description or line.account_name
            )
            db.add(db_line)

        # Audit trail recording
        audit_record = AuditLog(
            tenant_id=tenant_id,
            entity_name="JournalEntry",
            entity_id=db_entry.id,
            action="POST",
            performed_by=posted_by,
            details=f"Posted entry for invoice #{proposal.invoice_number}. Total Debits/Credits: INR {proposal.total_debits}"
        )
        db.add(audit_record)

        db.commit()
        db.refresh(db_entry)
        return db_entry
    except Exception as e:
        db.rollback()
        raise e


def generate_trial_balance(
    db: Session,
    tenant_id: str,
    as_of_date: Optional[date] = None,
    financial_year: Optional[str] = None
) -> TrialBalanceReport:
    """
    Calculates the authoritative Trial Balance dynamically from posted journal lines.
    Zero precomputed cached balances; derives truth directly from double-entry history.
    Supports filtering by as_of_date and financial_year.
    """
    if as_of_date is None:
        as_of_date = date.today()

    accounts = db.query(Account).filter(Account.tenant_id == tenant_id).all()
    account_map = {acc.id: acc for acc in accounts}

    # Query posted journal lines up to as_of_date
    query = (
        db.query(JournalLine)
        .join(JournalEntry)
        .filter(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.status == EntryPostingStatus.POSTED,
            JournalEntry.entry_date <= as_of_date
        )
    )
    if financial_year:
        query = query.filter(JournalEntry.financial_year == financial_year)

    lines = query.all()

    balances: Dict[str, Dict[str, Decimal]] = {
        acc_id: {"debit": Decimal("0.00"), "credit": Decimal("0.00")} for acc_id in account_map
    }

    for line in lines:
        if line.entry_type == EntryType.DEBIT:
            balances[line.account_id]["debit"] += Decimal(str(line.amount))
        else:
            balances[line.account_id]["credit"] += Decimal(str(line.amount))

    tb_rows: List[LedgerAccountBalance] = []
    for acc_id, totals in balances.items():
        acc = account_map[acc_id]
        tot_dr = totals["debit"].quantize(Decimal("0.01"))
        tot_cr = totals["credit"].quantize(Decimal("0.01"))

        if tot_dr == Decimal("0.00") and tot_cr == Decimal("0.00"):
            continue

        if acc.normal_balance == NormalBalance.DEBIT:
            net_balance = (tot_dr - tot_cr).quantize(Decimal("0.01"))
            balance_type = "DEBIT" if net_balance >= Decimal("0.00") else "CREDIT"
            net_balance = abs(net_balance)
        else:
            net_balance = (tot_cr - tot_dr).quantize(Decimal("0.01"))
            balance_type = "CREDIT" if net_balance >= Decimal("0.00") else "DEBIT"
            net_balance = abs(net_balance)

        tb_rows.append(
            LedgerAccountBalance(
                account_code=acc.code,
                account_name=acc.name,
                category=acc.category.value,
                total_debits=tot_dr,
                total_credits=tot_cr,
                closing_balance=net_balance,
                balance_type=balance_type
            )
        )

    tb_rows.sort(key=lambda x: x.account_code)
    return TrialBalanceReport.from_rows(as_of_date=as_of_date, rows=tb_rows)


def post_settlement_entry(
    db: Session,
    tenant_id: str,
    invoice_id: str,
    payment_account_code: str = "1020",
    payment_date: Optional[date] = None,
    amount: Optional[Decimal] = None,
    payment_reference: str = "BANK_TXN",
    posted_by: str = "USER_SETTLEMENT"
) -> JournalEntry:
    """
    Atomically records cash/bank settlement against an invoice, reconciling
    Accounts Payable or Accounts Receivable and updating invoice payment status.
    """
    from app.models.accounting import Invoice

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id).first()
    if not invoice:
        raise InvariantViolation("Invoice not found for settlement.")

    settle_date = payment_date or date.today()
    fy = get_financial_year(settle_date)
    settle_amount = amount if amount is not None else (invoice.grand_total - invoice.amount_paid)
    if settle_amount <= Decimal("0.00"):
        raise InvariantViolation("Settlement amount must be positive.")

    # Find accounts
    pay_acc = db.query(Account).filter(Account.tenant_id == tenant_id, Account.code == payment_account_code, Account.is_active == True).first()
    if not pay_acc:
        raise InvariantViolation(f"Settlement account code '{payment_account_code}' not found in active Chart of Accounts.")

    is_sales = invoice.invoice_type == "SALES"
    lines_to_create = []

    if is_sales:
        # Clearing Customer Receivable: Debit Bank, Credit Accounts Receivable
        ar_acc = db.query(Account).filter(Account.tenant_id == tenant_id, Account.code == "1030", Account.is_active == True).first()
        if not ar_acc:
            raise InvariantViolation("Accounts Receivable account (code 1030) not found.")

        # Debit Cash/Bank
        lines_to_create.append(JournalLine(
            account_id=pay_acc.id,
            entry_type=EntryType.DEBIT,
            amount=settle_amount,
            description=f"Receipt from {invoice.buyer_name or 'Customer'} ref #{payment_reference}"
        ))
        # Credit Accounts Receivable
        lines_to_create.append(JournalLine(
            account_id=ar_acc.id,
            entry_type=EntryType.CREDIT,
            amount=settle_amount,
            description=f"Settlement for Sales Inv #{invoice.invoice_number}"
        ))
        narration = f"Being payment received against Sales Invoice #{invoice.invoice_number} via {pay_acc.name} (Ref: {payment_reference})"
    else:
        # Clearing Trade Payable: Debit Accounts Payable, Credit Bank
        ap_acc = db.query(Account).filter(Account.tenant_id == tenant_id, Account.code == "2010", Account.is_active == True).first()
        if not ap_acc:
            raise InvariantViolation("Accounts Payable account (code 2010) not found.")

        # Debit Accounts Payable
        lines_to_create.append(JournalLine(
            account_id=ap_acc.id,
            entry_type=EntryType.DEBIT,
            amount=settle_amount,
            description=f"Settlement to {invoice.vendor_name} for Inv #{invoice.invoice_number}"
        ))
        # Credit Cash/Bank
        lines_to_create.append(JournalLine(
            account_id=pay_acc.id,
            entry_type=EntryType.CREDIT,
            amount=settle_amount,
            description=f"Payment disbursed ref #{payment_reference}"
        ))
        narration = f"Being payment disbursed against Purchase Invoice #{invoice.invoice_number} via {pay_acc.name} (Ref: {payment_reference})"

    # Atomic DB posting
    try:
        db_entry = JournalEntry(
            tenant_id=tenant_id,
            document_id=invoice.document_id,
            invoice_id=invoice.id,
            invoice_number=f"PAY-{invoice.invoice_number}",
            entry_date=settle_date,
            financial_year=fy,
            payment_reference=payment_reference,
            transaction_type=TransactionType.SETTLEMENT_PAYMENT,
            narration=narration,
            status=EntryPostingStatus.POSTED,
            posted_at=datetime.now(timezone.utc)
        )
        db.add(db_entry)
        db.flush()

        for line in lines_to_create:
            line.entry_id = db_entry.id
            db.add(line)

        # Update invoice payment tracking
        invoice.amount_paid += settle_amount
        if invoice.amount_paid >= invoice.grand_total:
            invoice.payment_status = "PAID"
        else:
            invoice.payment_status = "PARTIALLY_PAID"

        # Record audit log
        audit_record = AuditLog(
            tenant_id=tenant_id,
            entity_name="JournalEntry",
            entity_id=db_entry.id,
            action="SETTLE",
            performed_by=posted_by,
            details=f"Settlement of INR {settle_amount} posted against Invoice #{invoice.invoice_number}. Status: {invoice.payment_status}"
        )
        db.add(audit_record)

        db.commit()
        db.refresh(db_entry)
        return db_entry
    except Exception as e:
        db.rollback()
        raise e
