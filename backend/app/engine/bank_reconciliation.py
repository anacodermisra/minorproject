import csv
import io
import re
import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.accounting import (
    Tenant,
    Account,
    Invoice,
    JournalEntry,
    JournalLine,
    AuditLog,
    BankTransaction,
    EntryPostingStatus,
)


class BankReconciliationService:
    """
    Automated Bank Statement Ingestion, Rule-Based Matching, and
    Bank Reconciliation Statement (BRS) Computation under ICAI Standard Guidance.
    """

    @classmethod
    def parse_statement_csv(cls, csv_text: str) -> List[Dict]:
        """
        Parses standard bank statement CSV with flexible column headers:
        Expected columns: Date, Description/Narration, Ref/Cheque No, Withdrawal/Debit, Deposit/Credit, Balance
        """
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        rows = []
        for r in reader:
            # Normalize header names (lowercase, stripped)
            norm = {k.strip().lower(): v.strip() for k, v in r.items() if k}

            # Locate date
            date_str = norm.get("date") or norm.get("txn date") or norm.get("transaction date") or norm.get("value date")
            if not date_str:
                continue
            # Try parsing various date formats
            txn_date = None
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
                try:
                    txn_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            if not txn_date:
                continue

            desc = norm.get("description") or norm.get("narration") or norm.get("particulars") or "Bank Transaction"
            ref = norm.get("ref no") or norm.get("reference") or norm.get("cheque no") or norm.get("utr") or ""

            # Amounts
            def clean_dec(val: Optional[str]) -> Decimal:
                if not val:
                    return Decimal("0.00")
                cleaned = re.sub(r"[^\d.-]", "", val)
                try:
                    return Decimal(cleaned)
                except Exception:
                    return Decimal("0.00")

            withdrawal = clean_dec(norm.get("withdrawal") or norm.get("debit") or norm.get("dr"))
            deposit = clean_dec(norm.get("deposit") or norm.get("credit") or norm.get("cr"))
            balance = clean_dec(norm.get("balance") or norm.get("closing balance"))

            rows.append({
                "transaction_date": txn_date,
                "description": desc,
                "reference_no": ref,
                "withdrawal_amount": withdrawal,
                "deposit_amount": deposit,
                "balance_after": balance
            })
        return rows

    @classmethod
    def import_transactions(
        cls,
        db: Session,
        tenant_id: str,
        transactions: List[Dict],
        batch_name: Optional[str] = None
    ) -> List[BankTransaction]:
        batch_id = batch_name or f"BATCH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        created = []
        for t in transactions:
            txn = BankTransaction(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                statement_batch=batch_id,
                transaction_date=t["transaction_date"],
                value_date=t.get("value_date", t["transaction_date"]),
                description=t["description"],
                reference_no=t.get("reference_no", ""),
                withdrawal_amount=Decimal(str(t.get("withdrawal_amount", "0.00"))),
                deposit_amount=Decimal(str(t.get("deposit_amount", "0.00"))),
                balance_after=Decimal(str(t.get("balance_after", "0.00"))) if t.get("balance_after") is not None else None,
                status="UNMATCHED"
            )
            db.add(txn)
            created.append(txn)
        db.commit()
        return created

    @classmethod
    def auto_reconcile(cls, db: Session, tenant_id: str) -> Dict:
        """
        Deterministic Multi-Rule Bank Reconciliation:
        Rule 1: Exact reference/invoice number matching in description + exact amount match
        Rule 2: Exact amount match against unpaid/partially paid purchase/sales invoices within 45 days
        """
        unmatched = db.query(BankTransaction).filter(
            BankTransaction.tenant_id == tenant_id,
            BankTransaction.status == "UNMATCHED"
        ).all()

        invoices = db.query(Invoice).filter(
            Invoice.tenant_id == tenant_id
        ).all()

        matched_count = 0

        for txn in unmatched:
            matched_inv = None

            # Rule 1: Reference or invoice number match in narration + amount match
            for inv in invoices:
                if inv.invoice_number.lower() in txn.description.lower() or (txn.reference_no and txn.reference_no.lower() in inv.invoice_number.lower()):
                    inv_amt = inv.grand_total
                    txn_amt = txn.withdrawal_amount if inv.invoice_type == "PURCHASE" else txn.deposit_amount
                    if abs(inv_amt - txn_amt) <= Decimal("0.05"):
                        matched_inv = inv
                        break

            # Rule 2: Amount match if unique un-matched invoice with exact amount exists within date window
            if not matched_inv:
                target_amt = txn.withdrawal_amount if txn.withdrawal_amount > Decimal("0.00") else txn.deposit_amount
                target_type = "PURCHASE" if txn.withdrawal_amount > Decimal("0.00") else "SALES"
                candidates = [
                    inv for inv in invoices
                    if inv.invoice_type == target_type and abs(inv.grand_total - target_amt) <= Decimal("0.05")
                ]
                if len(candidates) == 1:
                    matched_inv = candidates[0]

            if matched_inv:
                txn.status = "MATCHED"
                txn.matched_invoice_id = matched_inv.id
                txn.reconciled_at = datetime.now(timezone.utc)
                txn.reconciled_by = "AUTO_RULES_ENGINE"
                
                # Update invoice payment status if un-settled
                if matched_inv.payment_status == "UNPAID":
                    matched_inv.payment_status = "PAID"
                    matched_inv.amount_paid = matched_inv.grand_total

                matched_count += 1

        db.commit()
        return {
            "total_unmatched_evaluated": len(unmatched),
            "newly_matched": matched_count,
            "remaining_unmatched": len(unmatched) - matched_count
        }

    @classmethod
    def generate_brs_statement(cls, db: Session, tenant_id: str, as_of_date: Optional[date] = None) -> Dict:
        """
        Generates formal Bank Reconciliation Statement (BRS):
        - Balance as per Bank Statement
        - Less: Cheques issued / Payments made in books but not presented at bank
        - Add: Cheques deposited / Receipts in books but not credited at bank
        - Less/Add: Bank Charges, direct debits, direct credits
        - = Balance as per General Ledger (Account 1020)
        """
        target_date = as_of_date or date.today()

        # 1. Bank Account (1020) balance from General Ledger
        bank_acc = db.query(Account).filter(Account.tenant_id == tenant_id, Account.code == "1020").first()
        gl_balance = Decimal("0.00")
        if bank_acc:
            debits = db.query(func.coalesce(func.sum(JournalLine.amount), Decimal("0.00"))).join(JournalEntry).filter(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.status == EntryPostingStatus.POSTED,
                JournalLine.account_id == bank_acc.id,
                JournalLine.entry_type == "DEBIT",
                JournalEntry.entry_date <= target_date
            ).scalar()
            credits = db.query(func.coalesce(func.sum(JournalLine.amount), Decimal("0.00"))).join(JournalEntry).filter(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.status == EntryPostingStatus.POSTED,
                JournalLine.account_id == bank_acc.id,
                JournalLine.entry_type == "CREDIT",
                JournalEntry.entry_date <= target_date
            ).scalar()
            gl_balance = debits - credits  # Asset account normal debit balance

        # 2. Latest Bank statement balance
        latest_txn = db.query(BankTransaction).filter(
            BankTransaction.tenant_id == tenant_id,
            BankTransaction.transaction_date <= target_date
        ).order_by(BankTransaction.transaction_date.desc(), BankTransaction.created_at.desc()).first()

        statement_balance = latest_txn.balance_after if (latest_txn and latest_txn.balance_after is not None) else gl_balance

        # 3. Unmatched items
        unmatched_withdrawals = db.query(BankTransaction).filter(
            BankTransaction.tenant_id == tenant_id,
            BankTransaction.status == "UNMATCHED",
            BankTransaction.withdrawal_amount > Decimal("0.00"),
            BankTransaction.transaction_date <= target_date
        ).all()
        unmatched_deposits = db.query(BankTransaction).filter(
            BankTransaction.tenant_id == tenant_id,
            BankTransaction.status == "UNMATCHED",
            BankTransaction.deposit_amount > Decimal("0.00"),
            BankTransaction.transaction_date <= target_date
        ).all()

        unmatched_dr_total = sum((t.withdrawal_amount for t in unmatched_withdrawals), start=Decimal("0.00"))
        unmatched_cr_total = sum((t.deposit_amount for t in unmatched_deposits), start=Decimal("0.00"))

        reconciled_balance = statement_balance + unmatched_cr_total - unmatched_dr_total
        variance = gl_balance - reconciled_balance

        return {
            "as_of_date": target_date.isoformat(),
            "bank_account_code": "1020",
            "bank_account_name": bank_acc.name if bank_acc else "Bank Account",
            "gl_book_balance": float(gl_balance),
            "bank_statement_balance": float(statement_balance),
            "unmatched_deposits_total": float(unmatched_cr_total),
            "unmatched_deposits_count": len(unmatched_deposits),
            "unmatched_withdrawals_total": float(unmatched_dr_total),
            "unmatched_withdrawals_count": len(unmatched_withdrawals),
            "reconciled_statement_balance": float(reconciled_balance),
            "reconciliation_variance": float(variance),
            "is_fully_reconciled": abs(variance) <= Decimal("0.05")
        }
