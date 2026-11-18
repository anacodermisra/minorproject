import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db.seed_accounts import seed_standard_accounts
from app.models.accounting import Tenant, Account, Invoice, JournalEntry, EntryPostingStatus
from app.schemas.invoice import ExtractedInvoice, InvoiceLineItem
from app.schemas.accounting import EntryType, TransactionType
from app.engine.interpreter import AccountingInterpreter, get_financial_year
from app.engine.ledger import post_journal_entry, generate_trial_balance, post_settlement_entry
from app.engine.statements import FinancialStatementService


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    tenant = Tenant(
        name="Apex IT Solutions",
        gstin="07AAAAA0000A1Z5",
        currency="INR",
        business_type="IT_SERVICES"
    )
    session.add(tenant)
    session.commit()
    seed_standard_accounts(session, tenant.id)

    yield session, tenant
    session.close()


def test_financial_year_helper():
    assert get_financial_year(date(2026, 4, 1)) == "FY 2026-27"
    assert get_financial_year(date(2026, 10, 15)) == "FY 2026-27"
    assert get_financial_year(date(2027, 3, 31)) == "FY 2026-27"
    assert get_financial_year(date(2026, 1, 15)) == "FY 2025-26"
    assert get_financial_year(date(2026, 3, 31)) == "FY 2025-26"


def test_domain_aware_stationery_classification():
    item = InvoiceLineItem(
        description="A4 Copy Paper Reams (Pack of 10)",
        hsn_sac="4802",
        quantity=Decimal("10.00"),
        unit_price=Decimal("400.00"),
        total_amount=Decimal("4000.00")
    )

    # 1. For IT_SERVICES business -> Office Supplies Expense (5010)
    code_it, name_it, cat_it, exp_it, review_it = AccountingInterpreter.classify_line_item(
        item, business_type="IT_SERVICES"
    )
    assert code_it == "5010"
    assert "Office Supplies" in name_it

    # 2. For RETAIL_STATIONERY business -> Trading Inventory / COGS (5005)
    code_ret, name_ret, cat_ret, exp_ret, review_ret = AccountingInterpreter.classify_line_item(
        item, business_type="RETAIL_STATIONERY"
    )
    assert code_ret == "5005"
    assert "Purchases of Trading Goods" in name_ret
    assert "merchandise purchased for resale" in exp_ret


def test_sales_invoice_interpretation():
    invoice = ExtractedInvoice(
        invoice_number="INV-SALE-2026-001",
        invoice_date=date(2026, 11, 15),
        vendor_name="Apex IT Solutions",
        vendor_gstin="07AAAAA0000A1Z5",  # Delhi
        buyer_name="Client Corp",
        buyer_gstin="07BBBBB2222B1Z6",   # Delhi (Intra-state)
        place_of_supply="Delhi (07)",
        place_of_supply_state_code="07",
        subtotal=Decimal("100000.00"),
        total_tax=Decimal("18000.00"),
        grand_total=Decimal("118000.00"),
        line_items=[
            InvoiceLineItem(
                description="Custom Cloud Software Development",
                hsn_sac="998314",
                quantity=Decimal("1.00"),
                unit_price=Decimal("100000.00"),
                total_amount=Decimal("100000.00")
            )
        ]
    )

    proposal = AccountingInterpreter.interpret_invoice(
        invoice=invoice,
        business_type="IT_SERVICES",
        invoice_direction="SALES"
    )

    assert proposal.invoice_type == "SALES"
    assert proposal.financial_year == "FY 2026-27"
    assert proposal.transaction_type == TransactionType.SALES_CREDIT

    # Verify double entry
    # Debit: Accounts Receivable 1030 (118,000)
    ar_lines = [l for l in proposal.lines if l.account_code == "1030" and l.entry_type == EntryType.DEBIT]
    assert len(ar_lines) == 1
    assert ar_lines[0].amount == Decimal("118000.00")

    # Credit: Sales Revenue 4010 (100,000)
    rev_lines = [l for l in proposal.lines if l.account_code == "4010" and l.entry_type == EntryType.CREDIT]
    assert len(rev_lines) == 1
    assert rev_lines[0].amount == Decimal("100000.00")

    # Credit: Output CGST 2081 (9,000) and Output SGST 2082 (9,000)
    cgst_lines = [l for l in proposal.lines if l.account_code == "2081" and l.entry_type == EntryType.CREDIT]
    sgst_lines = [l for l in proposal.lines if l.account_code == "2082" and l.entry_type == EntryType.CREDIT]
    assert len(cgst_lines) == 1 and cgst_lines[0].amount == Decimal("9000.00")
    assert len(sgst_lines) == 1 and sgst_lines[0].amount == Decimal("9000.00")


def test_settlement_reconciliation_cycle(test_db):
    db, tenant = test_db

    # 1. Create and post purchase invoice
    inv = Invoice(
        tenant_id=tenant.id,
        invoice_number="NOS-2026-999",
        invoice_date=date(2026, 10, 10),
        vendor_name="Office World Ltd",
        vendor_gstin="07XYZAB1234K1Z1",
        subtotal=Decimal("10000.00"),
        total_tax=Decimal("1800.00"),
        grand_total=Decimal("11800.00"),
        invoice_type="PURCHASE",
        payment_status="UNPAID",
        amount_paid=Decimal("0.00"),
        financial_year="FY 2026-27"
    )
    db.add(inv)
    db.commit()

    # 2. Settle the invoice partially
    entry1 = post_settlement_entry(
        db=db,
        tenant_id=tenant.id,
        invoice_id=inv.id,
        payment_account_code="1020",
        payment_date=date(2026, 10, 20),
        amount=Decimal("5000.00"),
        payment_reference="NEFT-001"
    )
    db.refresh(inv)
    assert inv.payment_status == "PARTIALLY_PAID"
    assert inv.amount_paid == Decimal("5000.00")

    # 3. Settle remainder
    entry2 = post_settlement_entry(
        db=db,
        tenant_id=tenant.id,
        invoice_id=inv.id,
        payment_account_code="1020",
        payment_date=date(2026, 10, 25),
        amount=Decimal("6800.00"),
        payment_reference="NEFT-002"
    )
    db.refresh(inv)
    assert inv.payment_status == "PAID"
    assert inv.amount_paid == Decimal("11800.00")


def test_monthly_analytics_and_statements(test_db):
    db, tenant = test_db
    analytics = FinancialStatementService.generate_monthly_analytics(db, tenant.id, financial_year="FY 2026-27")
    assert len(analytics) == 12
    assert analytics[0]["month_short"] == "Apr"
    assert analytics[11]["month_short"] == "Mar"
