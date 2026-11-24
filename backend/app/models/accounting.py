import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    Numeric,
    Boolean,
    ForeignKey,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.schemas.accounting import AccountCategory, NormalBalance, EntryType, TransactionType


def utc_now():
    return datetime.now(timezone.utc)


class Tenant(Base):
    """Represents a business or tenant entity."""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    gstin = Column(String(15), nullable=True, unique=True)
    currency = Column(String(3), default="INR", nullable=False)
    business_type = Column(String(50), default="IT_SERVICES", nullable=False)  # IT_SERVICES, RETAIL_STATIONERY, FURNITURE_RETAILER, GENERAL_ENTERPRISE
    created_at = Column(DateTime, default=utc_now)

    accounts = relationship("Account", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="tenant", cascade="all, delete-orphan")
    period_locks = relationship("PeriodLock", back_populates="tenant", cascade="all, delete-orphan")
    bank_transactions = relationship("BankTransaction", back_populates="tenant", cascade="all, delete-orphan")
    gstr2b_entries = relationship("Gstr2bEntry", back_populates="tenant", cascade="all, delete-orphan")


class Account(Base):
    """Chart of Accounts (General Ledger Account)."""
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    code = Column(String(20), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(SQLEnum(AccountCategory), nullable=False)
    normal_balance = Column(SQLEnum(NormalBalance), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)

    tenant = relationship("Tenant", back_populates="accounts")
    journal_lines = relationship("JournalLine", back_populates="account")


class DocumentStatus(str):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    POSTED = "POSTED"
    REJECTED = "REJECTED"


class Document(Base):
    """An uploaded invoice or financial document."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=True, index=True)  # SHA-256 for duplicate upload detection
    mime_type = Column(String(50), default="application/pdf")
    status = Column(String(30), default=DocumentStatus.UPLOADED, nullable=False)
    uploaded_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="documents")
    invoice = relationship("Invoice", uselist=False, back_populates="document", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="document")


class Invoice(Base):
    """Persisted invoice metadata and totals."""
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True, unique=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    
    invoice_number = Column(String(100), nullable=False, index=True)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)

    vendor_name = Column(String(255), nullable=False)
    vendor_gstin = Column(String(15), nullable=True)
    vendor_address = Column(Text, nullable=True)

    buyer_name = Column(String(255), nullable=True)
    buyer_gstin = Column(String(15), nullable=True)

    subtotal = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    total_tax = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    total_discount = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    grand_total = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))

    # Invoice classification & reconciliation
    invoice_type = Column(String(20), default="PURCHASE", nullable=False)  # PURCHASE or SALES
    payment_status = Column(String(20), default="UNPAID", nullable=False)  # UNPAID, PARTIALLY_PAID, PAID
    amount_paid = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    financial_year = Column(String(20), nullable=True, index=True)  # e.g. "FY 2026-27"

    confidence_score = Column(Numeric(5, 2), default=Decimal("1.00"))
    validation_flags = Column(Text, nullable=True)  # JSON-encoded array of warnings

    document = relationship("Document", back_populates="invoice")
    line_items = relationship("LineItem", back_populates="invoice", cascade="all, delete-orphan")


class LineItem(Base):
    """Persisted invoice table line-item."""
    __tablename__ = "line_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False)

    description = Column(String(500), nullable=False)
    hsn_sac = Column(String(20), nullable=True)
    quantity = Column(Numeric(12, 2), default=Decimal("1.00"), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    discount_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    tax_rate_percent = Column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="line_items")


class EntryPostingStatus(str):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class JournalEntry(Base):
    """The authoritative double-entry transaction record."""
    __tablename__ = "journal_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    
    invoice_number = Column(String(100), nullable=False)
    entry_date = Column(Date, nullable=False)
    financial_year = Column(String(20), nullable=True, index=True)
    payment_reference = Column(String(100), nullable=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    narration = Column(Text, nullable=False)
    status = Column(String(20), default=EntryPostingStatus.PROPOSED, nullable=False)
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="journal_entries")
    document = relationship("Document", back_populates="journal_entries")
    lines = relationship("JournalLine", back_populates="entry", cascade="all, delete-orphan")


class JournalLine(Base):
    """A single debit or credit line in an authoritative journal entry."""
    __tablename__ = "journal_lines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entry_id = Column(String(36), ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    
    entry_type = Column(SQLEnum(EntryType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(String(255), nullable=True)

    entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="journal_lines")


class AuditLog(Base):
    """Immutable audit trail for financial accountability."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    entity_name = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    action = Column(String(50), nullable=False)  # e.g. PROPOSE, APPROVE, EDIT, POST, REJECT, REVERSE, LOCK
    performed_by = Column(String(100), default="SYSTEM")
    user_role = Column(String(50), default="MAKER", nullable=True)  # MAKER, CHECKER, ADMIN, AUDITOR
    previous_state = Column(Text, nullable=True)  # JSON-encoded state before mutation
    new_state = Column(Text, nullable=True)  # JSON-encoded state after mutation
    details = Column(Text, nullable=True)  # Context description
    timestamp = Column(DateTime, default=utc_now)


class PeriodLock(Base):
    """Accounting Period Lock to enforce month-end close immutability."""
    __tablename__ = "period_locks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    period_key = Column(String(20), nullable=False, index=True)  # e.g. "2026-10", "2026-11", "FY 2026-27"
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String(100), nullable=True)
    lock_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="period_locks")


class BankTransaction(Base):
    """Imported bank feed/statement transaction for Bank Reconciliation (BRS)."""
    __tablename__ = "bank_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    statement_batch = Column(String(100), nullable=True)
    transaction_date = Column(Date, nullable=False)
    value_date = Column(Date, nullable=True)
    description = Column(String(500), nullable=False)
    reference_no = Column(String(100), nullable=True)  # UTR, Cheque No, Ref ID
    withdrawal_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)  # Debit from bank
    deposit_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)     # Credit to bank
    balance_after = Column(Numeric(15, 2), nullable=True)

    # Reconciliation status: UNMATCHED, MATCHED, MANUALLY_MATCHED, EXCLUDED
    status = Column(String(30), default="UNMATCHED", nullable=False)
    matched_invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    matched_journal_entry_id = Column(String(36), ForeignKey("journal_entries.id"), nullable=True)
    reconciled_at = Column(DateTime, nullable=True)
    reconciled_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="bank_transactions")


class Gstr2bEntry(Base):
    """GSTR-2B static statement and IMS (Invoice Management System) action record."""
    __tablename__ = "gstr2b_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    return_period = Column(String(10), nullable=False, index=True)  # e.g. "102026" or "2026-10"

    supplier_gstin = Column(String(15), nullable=False, index=True)
    supplier_name = Column(String(255), nullable=False)
    invoice_number = Column(String(100), nullable=False, index=True)
    invoice_type = Column(String(20), default="B2B", nullable=False)  # B2B, B2BA, CDNR, CDNRA
    invoice_date = Column(Date, nullable=False)

    invoice_value = Column(Numeric(15, 2), nullable=False)
    taxable_value = Column(Numeric(15, 2), nullable=False)
    igst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    cgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    sgst_amount = Column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)

    itc_availability = Column(String(5), default="Y", nullable=False)  # "Y" or "N"
    itc_blocked_reason = Column(String(255), nullable=True)

    # IMS (Invoice Management System) Status: NO_ACTION, ACCEPTED, REJECTED, PENDING
    ims_action = Column(String(30), default="NO_ACTION", nullable=False)
    ims_action_at = Column(DateTime, nullable=True)
    ims_action_by = Column(String(100), nullable=True)

    # Reconciliation link to internal purchase register: MATCHED, IN_GSTR2B_ONLY, VALUE_MISMATCH
    reconciliation_status = Column(String(30), default="GSTR2B_ONLY", nullable=False)
    matched_invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="gstr2b_entries")


