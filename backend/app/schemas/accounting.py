from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field


class AccountCategory(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class NormalBalance(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class EntryType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class ValidationCheckStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class ValidationCheckResult(BaseModel):
    """Detailed result of an individual invariant or accounting check."""
    check_name: str
    status: ValidationCheckStatus
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    difference: Optional[str] = None
    explanation: str
    source_fields: List[str] = Field(default_factory=list)
    requires_human_review: bool = False


class DocumentValidationReport(BaseModel):
    """Comprehensive validation summary evaluated prior to posting gate."""
    is_valid: bool = True
    can_post_automatically: bool = True
    has_blocking_failures: bool = False
    checks: List[ValidationCheckResult] = Field(default_factory=list)
    summary_message: str = "All validation checks passed."


class TransactionType(str, Enum):
    PURCHASE_GOODS_CREDIT = "PURCHASE_GOODS_CREDIT"
    PURCHASE_GOODS_CASH = "PURCHASE_GOODS_CASH"
    EXPENSE_OFFICE_CREDIT = "EXPENSE_OFFICE_CREDIT"
    EXPENSE_OFFICE_CASH = "EXPENSE_OFFICE_CASH"
    ASSET_ACQUISITION_CREDIT = "ASSET_ACQUISITION_CREDIT"
    ASSET_ACQUISITION_CASH = "ASSET_ACQUISITION_CASH"
    SALES_REVENUE = "SALES_REVENUE"
    SALES_CREDIT = "SALES_CREDIT"
    SETTLEMENT_PAYMENT = "SETTLEMENT_PAYMENT"
    TAX_PAYMENT = "TAX_PAYMENT"
    REVERSAL = "REVERSAL"
    UNCERTAIN = "UNCERTAIN"


class ChartOfAccount(BaseModel):
    """Represents a valid account in the General Ledger."""
    account_code: str = Field(..., description="e.g. 1001, 2001")
    account_name: str = Field(..., description="e.g. Office Furniture A/c, Input CGST A/c")
    category: AccountCategory
    normal_balance: NormalBalance
    is_active: bool = True
    description: Optional[str] = None


class ProposedJournalLine(BaseModel):
    """A single debit or credit line in a proposed entry."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    account_code: str
    account_name: str
    entry_type: EntryType
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Positive decimal value")
    description: Optional[str] = None

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, v):
        if isinstance(v, (int, float, str)):
            return Decimal(str(v)).quantize(Decimal("0.01"))
        return v


class ProposedJournalEntry(BaseModel):
    """A complete double-entry transaction proposal."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    entry_id: Optional[str] = None
    source_document_id: Optional[str] = None
    invoice_number: str
    entry_date: date
    financial_year: Optional[str] = None
    transaction_type: TransactionType
    narration: str = Field(..., description="Accounting explanation of the entry")
    lines: List[ProposedJournalLine] = Field(..., min_length=2)

    # Explainability & Trust
    reasoning: str = Field(default="Double-entry journal transaction", description="AI explanation of why this accounting treatment was chosen")
    applied_rules: List[str] = Field(default_factory=list, description="IDs/names of rules applied")
    requires_human_review: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    itc_recoverable: bool = True
    supplier_gstin: Optional[str] = None
    place_of_supply: Optional[str] = None
    invoice_type: str = "PURCHASE"
    validation_report: Optional[DocumentValidationReport] = None

    @computed_field
    @property
    def total_debits(self) -> Decimal:
        return sum(
            (line.amount for line in self.lines if line.entry_type == EntryType.DEBIT),
            start=Decimal("0.00")
        ).quantize(Decimal("0.01"))

    @computed_field
    @property
    def total_credits(self) -> Decimal:
        return sum(
            (line.amount for line in self.lines if line.entry_type == EntryType.CREDIT),
            start=Decimal("0.00")
        ).quantize(Decimal("0.01"))

    @computed_field
    @property
    def is_balanced(self) -> bool:
        return self.total_debits == self.total_credits
