import os
from decimal import Decimal
from datetime import date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.accounting import Tenant, Account, JournalEntry, JournalLine, AuditLog
from app.schemas.accounting import (
    ProposedJournalEntry,
    ProposedJournalLine,
    EntryType,
    TransactionType,
    ValidationCheckStatus,
)
from app.schemas.invoice import (
    ExtractedInvoice,
    InvoiceLineItem,
    TaxBreakdown,
    ExtractionConfidence,
)
from app.db.seed_accounts import seed_standard_accounts, STANDARD_CHART_OF_ACCOUNTS
from app.engine.interpreter import AccountingInterpreter, AccountingPolicy
from app.engine.invariants import (
    validate_double_entry_invariants,
    validate_line_item_math,
    validate_invoice_reconciliation,
    validate_gst_treatment,
    validate_journal_invariants_detailed,
    run_comprehensive_validation,
    InvariantViolation,
    DuplicateInvoiceViolation,
)
from app.engine.ledger import post_journal_entry


@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_tenant(db_session):
    tenant = Tenant(name="Modern Tech Solutions Private Limited", gstin="09AAFCM7314R1Z2", currency="INR")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    seed_standard_accounts(db_session, tenant.id)
    return tenant


# 1. Correct intra-state invoice with CGST and SGST
def test_intra_state_cgst_sgst():
    invoice = ExtractedInvoice(
        invoice_number="INV-INTRA-01",
        invoice_date=date(2026, 10, 18),
        vendor_name="Delhi Office Suppliers",
        vendor_gstin="07AAAAA1111A1Z1",  # Delhi (07)
        buyer_name="Tech Co",
        buyer_gstin="07BBBBB2222B1Z2",   # Delhi (07)
        place_of_supply="Delhi (07)",
        place_of_supply_state_code="07",
        subtotal=Decimal("10000.00"),
        total_tax=Decimal("1800.00"),
        grand_total=Decimal("11800.00"),
        line_items=[
            InvoiceLineItem(description="Paper reams", quantity=Decimal("20.00"), unit_price=Decimal("500.00"), total_amount=Decimal("10000.00"))
        ],
        taxes=[
            TaxBreakdown(tax_type="CGST", rate_percent=Decimal("9.00"), taxable_amount=Decimal("10000.00"), tax_amount=Decimal("900.00")),
            TaxBreakdown(tax_type="SGST", rate_percent=Decimal("9.00"), taxable_amount=Decimal("10000.00"), tax_amount=Decimal("900.00")),
        ]
    )

    entry = AccountingInterpreter.interpret_invoice(invoice)
    # Check that intra-state has CGST and SGST
    codes = [l.account_code for l in entry.lines]
    assert "1081" in codes  # Input CGST
    assert "1082" in codes  # Input SGST
    assert "1083" not in codes  # No IGST
    assert entry.is_balanced is True
    assert entry.total_debits == Decimal("11800.00")


# 2. Valid inter-state invoice with IGST
def test_inter_state_igst():
    invoice = ExtractedInvoice(
        invoice_number="INV-INTER-01",
        invoice_date=date(2026, 10, 18),
        vendor_name="Mumbai Cloud Systems",
        vendor_gstin="27CCCCCC3333C1Z3",  # Maharashtra (27)
        buyer_name="Tech Co",
        buyer_gstin="07BBBBB2222B1Z2",   # Delhi (07)
        place_of_supply="Delhi (07)",
        place_of_supply_state_code="07",
        subtotal=Decimal("20000.00"),
        total_tax=Decimal("3600.00"),
        grand_total=Decimal("23600.00"),
        line_items=[
            InvoiceLineItem(description="Cloud Server Hosting", quantity=Decimal("1.00"), unit_price=Decimal("20000.00"), total_amount=Decimal("20000.00"))
        ],
        taxes=[
            TaxBreakdown(tax_type="IGST", rate_percent=Decimal("18.00"), taxable_amount=Decimal("20000.00"), tax_amount=Decimal("3600.00")),
        ]
    )

    entry = AccountingInterpreter.interpret_invoice(invoice)
    codes = [l.account_code for l in entry.lines]
    assert "1083" in codes  # Input IGST
    assert "1081" not in codes
    assert "1082" not in codes
    assert entry.is_balanced is True
    assert entry.total_debits == Decimal("23600.00")


# 3. Purchase strictly above the capitalization threshold (> 10,000) capitalized
def test_capitalization_strictly_above_threshold():
    item = InvoiceLineItem(
        description="High-end Executive Desk",
        quantity=Decimal("1.00"),
        unit_price=Decimal("15000.00"),
        total_amount=Decimal("15000.00")
    )
    acc_code, acc_name, cat, exp, needs_review = AccountingInterpreter.classify_line_item(item)
    assert acc_code == "1050"  # Office Furniture & Fixtures
    assert cat.value == "ASSET"
    assert "Capitalized as Fixed Asset" in exp
    assert needs_review is False


# 4. Purchase exactly at the threshold (= 10,000) not capitalized under > 10k rule
def test_capitalization_boundary_at_threshold():
    item = InvoiceLineItem(
        description="Standard Office Table",
        quantity=Decimal("1.00"),
        unit_price=Decimal("10000.00"),
        total_amount=Decimal("10000.00")
    )
    acc_code, acc_name, cat, exp, needs_review = AccountingInterpreter.classify_line_item(item)
    # Unit eligible cost is not strictly greater than 10,000, so expensed
    assert acc_code == "5010"
    assert cat.value == "EXPENSE"
    assert "at or below capitalization threshold" in exp


# 5. Low-value durable item classified by nature, not blindly becoming Office Supplies
def test_low_value_durable_item_nature_classified():
    # USB-C Docking station is an IT peripheral costing 8,500
    item = InvoiceLineItem(
        description="USB-C docking station 12-in-1",
        hsn_sac="8471",
        quantity=Decimal("1.00"),
        unit_price=Decimal("8500.00"),
        total_amount=Decimal("8500.00")
    )
    acc_code, acc_name, cat, exp, needs_review = AccountingInterpreter.classify_line_item(item)
    assert acc_code == "5060"  # Computer Accessories & Peripherals Expense (NOT 5010 Office Supplies!)
    assert cat.value == "EXPENSE"
    assert "Computer Accessories" in acc_name


# 6. Unknown / ambiguous item routed to review
def test_unknown_item_routes_to_human_review():
    item = InvoiceLineItem(
        description="Specialized Quantum Gizmo Model X-99",
        quantity=Decimal("1.00"),
        unit_price=Decimal("4500.00"),
        total_amount=Decimal("4500.00")
    )
    acc_code, acc_name, cat, exp, needs_review = AccountingInterpreter.classify_line_item(item)
    assert needs_review is True
    assert "routed to human review" in exp


# 7. Recoverable vs uncertain/nonrecoverable input GST treatment
def test_itc_recoverable_vs_blocked():
    # Invoice for outdoor catering (Blocked under Section 17(5))
    blocked_invoice = ExtractedInvoice(
        invoice_number="INV-CAT-01",
        invoice_date=date(2026, 10, 18),
        vendor_name="Gourmet Catering Services",
        vendor_gstin="07AAAAA1111A1Z1",
        buyer_name="Tech Co",
        buyer_gstin="07BBBBB2222B1Z2",
        subtotal=Decimal("10000.00"),
        total_tax=Decimal("1800.00"),
        grand_total=Decimal("11800.00"),
        line_items=[
            InvoiceLineItem(description="Corporate Event Food Catering", quantity=Decimal("1.00"), unit_price=Decimal("10000.00"), total_amount=Decimal("10000.00"))
        ]
    )

    entry = AccountingInterpreter.interpret_invoice(blocked_invoice)
    assert entry.itc_recoverable is False
    assert entry.requires_human_review is True
    # Tax should be debited to 5080 (Ineligible GST), NOT 1081/1082 Input Tax Asset!
    codes = [l.account_code for l in entry.lines]
    assert "5080" in codes
    assert "1081" not in codes


# 8. Line-level quantity, rate, or discount mismatch detected
def test_line_level_arithmetic_mismatch_detected():
    item = InvoiceLineItem(
        description="Test Item",
        quantity=Decimal("2.00"),
        unit_price=Decimal("500.00"),
        discount_amount=Decimal("50.00"),
        total_amount=Decimal("1200.00")  # (2 * 500) - 50 = 950, not 1200
    )
    results = validate_line_item_math(item)
    assert any(r.status == ValidationCheckStatus.FAIL and "Arithmetic Reconciliation" in r.check_name for r in results)


# 9. Incorrect taxable subtotal detected
def test_incorrect_taxable_subtotal_detected():
    invoice = ExtractedInvoice(
        invoice_number="INV-MATH-01",
        invoice_date=date(2026, 10, 18),
        vendor_name="Vendor A",
        subtotal=Decimal("20000.00"),  # Actual lines sum to 10000!
        total_tax=Decimal("1800.00"),
        grand_total=Decimal("21800.00"),
        line_items=[
            InvoiceLineItem(description="Item 1", quantity=Decimal("10.00"), unit_price=Decimal("1000.00"), total_amount=Decimal("10000.00"))
        ]
    )
    reconcil_results = validate_invoice_reconciliation(invoice)
    assert any(r.status == ValidationCheckStatus.FAIL and "Subtotal Reconciliation" in r.check_name for r in reconcil_results)


# 10. Incorrect GST total detected
def test_incorrect_gst_total_detected():
    invoice = ExtractedInvoice(
        invoice_number="INV-GST-01",
        invoice_date=date(2026, 10, 18),
        vendor_name="Vendor A",
        subtotal=Decimal("10000.00"),
        total_tax=Decimal("1800.00"),
        grand_total=Decimal("11800.00"),
        taxes=[
            TaxBreakdown(tax_type="CGST", rate_percent=Decimal("9.00"), taxable_amount=Decimal("10000.00"), tax_amount=Decimal("500.00")),
            TaxBreakdown(tax_type="SGST", rate_percent=Decimal("9.00"), taxable_amount=Decimal("10000.00"), tax_amount=Decimal("500.00")),
        ]  # Sum of components is 1000, but declared is 1800!
    )
    reconcil_results = validate_invoice_reconciliation(invoice)
    assert any(r.status == ValidationCheckStatus.FAIL and "Tax Component Breakdown" in r.check_name for r in reconcil_results)


# 11. Incorrect invoice grand total detected
def test_incorrect_grand_total_detected():
    invoice = ExtractedInvoice(
        invoice_number="INV-GT-01",
        invoice_date=date(2026, 10, 18),
        vendor_name="Vendor A",
        subtotal=Decimal("10000.00"),
        total_tax=Decimal("1800.00"),
        grand_total=Decimal("15000.00")  # 10k + 1.8k = 11.8k != 15k!
    )
    reconcil_results = validate_invoice_reconciliation(invoice)
    assert any(r.status == ValidationCheckStatus.FAIL and "Grand Total Reconciliation" in r.check_name for r in reconcil_results)


# 12. Missing product row flagged
def test_missing_product_row_flagged():
    invoice = ExtractedInvoice(
        invoice_number="INV-EMPTY-01",
        invoice_date=date(2026, 10, 18),
        vendor_name="Vendor A",
        subtotal=Decimal("5000.00"),
        total_tax=Decimal("900.00"),
        grand_total=Decimal("5900.00"),
        line_items=[]  # Empty!
    )
    reconcil_results = validate_invoice_reconciliation(invoice)
    assert any(r.status == ValidationCheckStatus.WARNING and "Line Items Presence" in r.check_name for r in reconcil_results)


# 13. Summary/footer row contamination detected
def test_summary_footer_row_contamination_detected():
    invoice = ExtractedInvoice(
        invoice_number="INV-FOOTER-01",
        invoice_date=date(2026, 10, 18),
        vendor_name="Vendor A",
        subtotal=Decimal("5000.00"),
        grand_total=Decimal("5000.00"),
        line_items=[
            InvoiceLineItem(description="Real Product", quantity=Decimal("1.00"), unit_price=Decimal("5000.00"), total_amount=Decimal("5000.00")),
            InvoiceLineItem(description="Subtotal Amount", quantity=Decimal("1.00"), unit_price=Decimal("5000.00"), total_amount=Decimal("5000.00")),
        ]
    )
    reconcil_results = validate_invoice_reconciliation(invoice)
    assert any(r.status == ValidationCheckStatus.FAIL and "Summary Row Contamination" in r.check_name for r in reconcil_results)


# 14. Balanced journal with incorrect invoice amount blocked
def test_balanced_journal_with_incorrect_invoice_amount_blocked():
    invoice = ExtractedInvoice(
        invoice_number="INV-RECON-01",
        invoice_date=date(2026, 10, 18),
        vendor_name="Vendor X",
        subtotal=Decimal("50000.00"),
        total_tax=Decimal("0.00"),
        grand_total=Decimal("50000.00")
    )
    # Proposal balances at 60,000 even though invoice is 50,000!
    entry = ProposedJournalEntry(
        source_document_id="doc_1",
        invoice_number="INV-RECON-01",
        entry_date=date(2026, 10, 18),
        transaction_type=TransactionType.EXPENSE_OFFICE_CREDIT,
        narration="Test",
        reasoning="Test",
        lines=[
            ProposedJournalLine(account_code="5010", account_name="Office Supplies", entry_type=EntryType.DEBIT, amount=Decimal("60000.00")),
            ProposedJournalLine(account_code="2010", account_name="Accounts Payable", entry_type=EntryType.CREDIT, amount=Decimal("60000.00")),
        ]
    )
    checks = validate_journal_invariants_detailed(entry, invoice=invoice)
    assert any(c.status == ValidationCheckStatus.FAIL and "Source Invoice Payable Reconciliation" in c.check_name for c in checks)


# 15. Unbalanced journal blocked
def test_unbalanced_journal_blocked():
    entry = ProposedJournalEntry(
        source_document_id="doc_1",
        invoice_number="INV-UNBAL-01",
        entry_date=date(2026, 10, 18),
        transaction_type=TransactionType.EXPENSE_OFFICE_CREDIT,
        narration="Test",
        reasoning="Test",
        lines=[
            ProposedJournalLine(account_code="5010", account_name="Office Supplies", entry_type=EntryType.DEBIT, amount=Decimal("1000.00")),
            ProposedJournalLine(account_code="2010", account_name="Accounts Payable", entry_type=EntryType.CREDIT, amount=Decimal("1200.00")),
        ]
    )
    checks = validate_journal_invariants_detailed(entry)
    assert any(c.status == ValidationCheckStatus.FAIL and "Double-Entry Balance Invariant" in c.check_name for c in checks)


# 16. Non-existent or inactive account in journal caught
def test_nonexistent_or_inactive_account_blocked():
    entry = ProposedJournalEntry(
        source_document_id="doc_1",
        invoice_number="INV-BAD-ACC",
        entry_date=date(2026, 10, 18),
        transaction_type=TransactionType.EXPENSE_OFFICE_CREDIT,
        narration="Test",
        reasoning="Test",
        lines=[
            ProposedJournalLine(account_code="9999", account_name="Nonexistent Account", entry_type=EntryType.DEBIT, amount=Decimal("1000.00")),
            ProposedJournalLine(account_code="2010", account_name="Accounts Payable", entry_type=EntryType.CREDIT, amount=Decimal("1000.00")),
        ]
    )
    active_codes = {"1010", "2010", "5010"}
    checks = validate_journal_invariants_detailed(entry, active_account_codes=active_codes)
    assert any(c.status == ValidationCheckStatus.FAIL and "Chart of Accounts Verification" in c.check_name for c in checks)


# 17. Duplicate invoice posting attempt blocked
def test_duplicate_invoice_posting_blocked(db_session, test_tenant):
    proposal = ProposedJournalEntry(
        source_document_id="doc_dup",
        invoice_number="INV-DUP-01",
        entry_date=date(2026, 10, 18),
        transaction_type=TransactionType.EXPENSE_OFFICE_CREDIT,
        narration="First posting",
        reasoning="Test",
        lines=[
            ProposedJournalLine(account_code="5010", account_name="Office Supplies & Stationery", entry_type=EntryType.DEBIT, amount=Decimal("1000.00")),
            ProposedJournalLine(account_code="2010", account_name="Accounts Payable / Creditors", entry_type=EntryType.CREDIT, amount=Decimal("1000.00")),
        ]
    )
    # Post first time: should succeed
    post_journal_entry(db_session, test_tenant.id, proposal, posted_by="TEST")

    # Post second time: must raise DuplicateInvoiceViolation!
    with pytest.raises(DuplicateInvoiceViolation) as exc_info:
        post_journal_entry(db_session, test_tenant.id, proposal, posted_by="TEST")
    assert "Duplicate Posting Blocked" in str(exc_info.value)


# 18. Failed posting rolls back database transaction atomically
def test_atomic_rollback_on_failed_posting(db_session, test_tenant):
    bad_proposal = ProposedJournalEntry(
        source_document_id="doc_fail",
        invoice_number="INV-FAIL-01",
        entry_date=date(2026, 10, 18),
        transaction_type=TransactionType.EXPENSE_OFFICE_CREDIT,
        narration="Bad entry",
        reasoning="Test",
        lines=[
            ProposedJournalLine(account_code="5010", account_name="Office Supplies & Stationery", entry_type=EntryType.DEBIT, amount=Decimal("1000.00")),
            ProposedJournalLine(account_code="2010", account_name="Accounts Payable / Creditors", entry_type=EntryType.CREDIT, amount=Decimal("1500.00")),
        ]
    )
    initial_entries = db_session.query(JournalEntry).count()
    initial_lines = db_session.query(JournalLine).count()

    with pytest.raises(InvariantViolation):
        post_journal_entry(db_session, test_tenant.id, bad_proposal, posted_by="TEST")

    # Ensure 0 records were added
    assert db_session.query(JournalEntry).count() == initial_entries
    assert db_session.query(JournalLine).count() == initial_lines


# 19. Idempotent account seeding
def test_idempotent_account_seeding(db_session, test_tenant):
    # First seed already happened in fixture
    count_1 = db_session.query(Account).filter(Account.tenant_id == test_tenant.id).count()
    assert count_1 >= 15

    # Re-run seed: should add 0 new accounts
    added_second_time = seed_standard_accounts(db_session, test_tenant.id)
    assert added_second_time == 0

    count_2 = db_session.query(Account).filter(Account.tenant_id == test_tenant.id).count()
    assert count_1 == count_2


# 20. Valid invoice passing all checks can be approved and posted
def test_valid_invoice_approved_and_posted(db_session, test_tenant):
    proposal = ProposedJournalEntry(
        source_document_id="doc_valid",
        invoice_number="INV-VALID-01",
        entry_date=date(2026, 10, 18),
        transaction_type=TransactionType.EXPENSE_OFFICE_CREDIT,
        narration="Valid stationery purchase",
        reasoning="All checks passed.",
        lines=[
            ProposedJournalLine(account_code="5010", account_name="Office Supplies & Stationery", entry_type=EntryType.DEBIT, amount=Decimal("2000.00")),
            ProposedJournalLine(account_code="2010", account_name="Accounts Payable / Creditors", entry_type=EntryType.CREDIT, amount=Decimal("2000.00")),
        ]
    )
    posted = post_journal_entry(db_session, test_tenant.id, proposal, posted_by="USER_REVIEWER")
    assert posted.id is not None
    assert posted.status == "POSTED"


# 21. REGRESSION TEST: The Northstar Office Systems Sample Invoice
def test_northstar_sample_invoice_regression():
    """
    Validates complete interpretation and accounting rules on the sample invoice:
    - Supplier: Northstar Office Systems (Noida UP, 09AABCN4821K1Z6)
    - Buyer: Modern Tech Solutions Private Limited (Greater Noida UP, 09AAFCM7314R1Z2)
    - Place of Supply: Uttar Pradesh (09)
    - Items:
      1. Executive ergonomic chair: Qty 3, Rate 6,200.00, Disc 10% (1,860), Taxable 16,740, GST 18%
         (Unit cost = 5,580 <= 10k -> expensed under nature, not capitalized!)
      2. USB-C docking station: Qty 2, Rate 8,500.00, Disc 5% (850), Taxable 16,150, GST 18%
         (Unit cost = 8,075 <= 10k -> Computer Accessories & Peripherals Code 5060, NOT capitalized!)
      3. A4 copier paper: Qty 5, Rate 1,250.00, Taxable 6,250, GST 12%
         (Office Supplies Code 5010)
      4. Braided USB-C cable: Qty 10, Rate 450.00, Disc 2% (90), Taxable 4,410, GST 18%
         (Computer Accessories Code 5060)
      5. Freight & handling: Qty 1, Rate 1,200.00, Taxable 1,200, GST 18%
         (Freight & Shipping Code 5050)
    - Subtotal: 44,750.00
    - CGST: 3,840.00
    - SGST: 3,840.00
    - Total GST: 7,680.00
    - Round off: 0.00
    - Grand Total: 52,430.00
    """
    invoice = ExtractedInvoice(
        invoice_number="NOS/26-27/0418",
        invoice_date=date(2026, 10, 18),
        due_date=date(2026, 11, 17),
        vendor_name="NORTHSTAR OFFICE SYSTEMS",
        vendor_gstin="09AABCN4821K1Z6",
        buyer_name="Modern Tech Solutions Private Limited",
        buyer_gstin="09AAFCM7314R1Z2",
        place_of_supply="Uttar Pradesh (09)",
        place_of_supply_state_code="09",
        payment_terms="30 days from invoice date",
        subtotal=Decimal("44750.00"),
        total_tax=Decimal("7680.00"),
        total_discount=Decimal("2800.00"),  # 1860 + 850 + 90 = 2800
        round_off=Decimal("0.00"),
        grand_total=Decimal("52430.00"),
        line_items=[
            InvoiceLineItem(
                item_id="CH-ERG-06",
                description="Executive ergonomic chair",
                hsn_sac="9401",
                quantity=Decimal("3.00"),
                unit_price=Decimal("6200.00"),
                discount_amount=Decimal("1860.00"),
                tax_rate_percent=Decimal("18.00"),
                total_amount=Decimal("16740.00")
            ),
            InvoiceLineItem(
                item_id="IT-DK-12",
                description="USB-C docking station, 12-in-1",
                hsn_sac="8471",
                quantity=Decimal("2.00"),
                unit_price=Decimal("8500.00"),
                discount_amount=Decimal("850.00"),
                tax_rate_percent=Decimal("18.00"),
                total_amount=Decimal("16150.00")
            ),
            InvoiceLineItem(
                item_id="ST-PAP-A4",
                description="A4 copier paper, 5-ream carton",
                hsn_sac="4802",
                quantity=Decimal("5.00"),
                unit_price=Decimal("1250.00"),
                discount_amount=Decimal("0.00"),
                tax_rate_percent=Decimal("12.00"),
                total_amount=Decimal("6250.00")
            ),
            InvoiceLineItem(
                item_id="CAB-C2M",
                description="Braided USB-C cable, 2 m",
                hsn_sac="8544",
                quantity=Decimal("10.00"),
                unit_price=Decimal("450.00"),
                discount_amount=Decimal("90.00"),
                tax_rate_percent=Decimal("18.00"),
                total_amount=Decimal("4410.00")
            ),
            InvoiceLineItem(
                item_id="NS-DEL-1810",
                description="Freight & handling",
                hsn_sac="9965",
                quantity=Decimal("1.00"),
                unit_price=Decimal("1200.00"),
                discount_amount=Decimal("0.00"),
                tax_rate_percent=Decimal("18.00"),
                total_amount=Decimal("1200.00")
            ),
        ],
        taxes=[
            TaxBreakdown(tax_type="CGST", rate_percent=Decimal("9.00"), taxable_amount=Decimal("38500.00"), tax_amount=Decimal("3465.00")),
            TaxBreakdown(tax_type="SGST", rate_percent=Decimal("9.00"), taxable_amount=Decimal("38500.00"), tax_amount=Decimal("3465.00")),
            TaxBreakdown(tax_type="CGST", rate_percent=Decimal("6.00"), taxable_amount=Decimal("6250.00"), tax_amount=Decimal("375.00")),
            TaxBreakdown(tax_type="SGST", rate_percent=Decimal("6.00"), taxable_amount=Decimal("6250.00"), tax_amount=Decimal("375.00")),
        ]
    )

    # 1. Interpret Accounting Treatment
    entry = AccountingInterpreter.interpret_invoice(invoice)

    # Line mappings checks:
    line_map = {l.account_code: l.amount for l in entry.lines}

    # Chairs (16,740) + Paper (6,250) -> 5010 Office Supplies (Low-value equipment + paper) = 22,990.00
    assert line_map["5010"] == Decimal("22990.00")

    # Docking stations (16,150) + Cables (4,410) -> 5060 Computer Accessories = 20,560.00
    assert line_map["5060"] == Decimal("20560.00")

    # Freight -> 5050 Freight Expense = 1,200.00
    assert line_map["5050"] == Decimal("1200.00")

    # GST: Intra-state UP to UP (09 to 09)
    # CGST = 3,465 + 375 = 3,840.00
    assert line_map["1081"] == Decimal("3840.00")
    # SGST = 3,465 + 375 = 3,840.00
    assert line_map["1082"] == Decimal("3840.00")

    # Accounts Payable: 52,430.00
    assert line_map["2010"] == Decimal("52430.00")

    # Balance check
    assert entry.total_debits == Decimal("52430.00")
    assert entry.total_credits == Decimal("52430.00")
    assert entry.is_balanced is True

    # 2. Run Comprehensive Invariant Validation Report
    active_codes = {acc["code"] for acc in STANDARD_CHART_OF_ACCOUNTS}
    report = run_comprehensive_validation(invoice, entry, active_account_codes=active_codes)

    assert report.is_valid is True
    assert report.has_blocking_failures is False
    assert report.can_post_automatically is True


# 22. Round-off Variance Dedicated Account 5090 Test
def test_round_off_variance_routing():
    """
    Verifies that invoice round-off fractions are routed strictly to 5090
    (Rounding Off & Fractional Variance) and never to operating expense 5010 or revenue 4010.
    """
    invoice_pos = ExtractedInvoice(
        invoice_number="INV-RO-POS",
        invoice_date=date(2026, 11, 1),
        vendor_name="National Tech",
        vendor_gstin="07AAAAA1111A1Z1",
        buyer_name="Modern Tech Solutions",
        buyer_gstin="07BBBBB2222B1Z2",
        place_of_supply="Delhi (07)",
        place_of_supply_state_code="07",
        subtotal=Decimal("1000.00"),
        total_tax=Decimal("180.00"),
        total_discount=Decimal("0.00"),
        round_off=Decimal("0.40"),  # Positive round off fraction
        grand_total=Decimal("1180.40"),
        line_items=[
            InvoiceLineItem(
                item_id="ITEM-1",
                description="Consumable Stationery",
                hsn_sac="4802",
                quantity=Decimal("1.00"),
                unit_price=Decimal("1000.00"),
                tax_rate_percent=Decimal("18.00"),
                total_amount=Decimal("1000.00")
            )
        ]
    )
    entry_pos = AccountingInterpreter.interpret_invoice(invoice_pos)
    line_map_pos = {l.account_code: (l.entry_type, l.amount) for l in entry_pos.lines}
    
    assert "5090" in line_map_pos
    assert line_map_pos["5090"] == (EntryType.DEBIT, Decimal("0.40"))
    assert entry_pos.is_balanced is True
    assert entry_pos.total_debits == Decimal("1180.40")

    # Negative round-off test (discount/credit adjustment)
    invoice_neg = ExtractedInvoice(
        invoice_number="INV-RO-NEG",
        invoice_date=date(2026, 11, 1),
        vendor_name="National Tech",
        vendor_gstin="07AAAAA1111A1Z1",
        buyer_name="Modern Tech Solutions",
        buyer_gstin="07BBBBB2222B1Z2",
        place_of_supply="Delhi (07)",
        place_of_supply_state_code="07",
        subtotal=Decimal("1000.00"),
        total_tax=Decimal("180.00"),
        total_discount=Decimal("0.00"),
        round_off=Decimal("-0.35"),  # Negative round off
        grand_total=Decimal("1179.65"),
        line_items=[
            InvoiceLineItem(
                item_id="ITEM-1",
                description="Consumable Stationery",
                hsn_sac="4802",
                quantity=Decimal("1.00"),
                unit_price=Decimal("1000.00"),
                tax_rate_percent=Decimal("18.00"),
                total_amount=Decimal("1000.00")
            )
        ]
    )
    entry_neg = AccountingInterpreter.interpret_invoice(invoice_neg)
    line_map_neg = {l.account_code: (l.entry_type, l.amount) for l in entry_neg.lines}

    assert "5090" in line_map_neg
    assert line_map_neg["5090"] == (EntryType.CREDIT, Decimal("0.35"))
    assert entry_neg.is_balanced is True
    assert entry_neg.total_debits == Decimal("1180.00")
    assert entry_neg.total_credits == Decimal("1180.00")

