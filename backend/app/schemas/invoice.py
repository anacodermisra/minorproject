from decimal import Decimal
from datetime import date
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ExtractionConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNCERTAIN = "UNCERTAIN"


class InvoiceLineItem(BaseModel):
    """Represents a single row in an invoice line-item table."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    item_id: Optional[str] = Field(default=None, description="SKU or item code if present")
    description: str = Field(..., description="Description of good or service")
    hsn_sac: Optional[str] = Field(default=None, description="HSN or SAC code for GST")
    quantity: Decimal = Field(default=Decimal("1.00"), description="Quantity purchased")
    unit: Optional[str] = Field(default="Unit", description="e.g. Pcs, Kgs, Hours")
    unit_price: Decimal = Field(..., description="Base price per unit before tax")
    discount_amount: Decimal = Field(default=Decimal("0.00"), description="Discount on this line")
    tax_rate_percent: Decimal = Field(default=Decimal("0.00"), description="GST rate percentage, e.g. 18.00")
    tax_amount: Decimal = Field(default=Decimal("0.00"), description="Tax amount for this line")
    total_amount: Decimal = Field(..., description="Final line total including or excluding tax based on invoice convention")

    @field_validator("quantity", "unit_price", "discount_amount", "tax_rate_percent", "tax_amount", "total_amount", mode="before")
    @classmethod
    def parse_to_decimal(cls, v):
        if v is None:
            return Decimal("0.00")
        if isinstance(v, (int, float, str)):
            return Decimal(str(v)).quantize(Decimal("0.01"))
        return v

    @property
    def discount(self) -> Decimal:
        """Convenience alias for discount_amount."""
        return self.discount_amount


class TaxBreakdown(BaseModel):
    """Detailed tax component breakdown (e.g. CGST, SGST, IGST)."""
    tax_type: str = Field(..., description="CGST, SGST, IGST, VAT, or TAX")
    rate_percent: Decimal = Field(default=Decimal("0.00"))
    taxable_amount: Decimal = Field(default=Decimal("0.00"))
    tax_amount: Decimal = Field(...)

    @field_validator("rate_percent", "taxable_amount", "tax_amount", mode="before")
    @classmethod
    def parse_to_decimal(cls, v):
        if v is None:
            return Decimal("0.00")
        return Decimal(str(v)).quantize(Decimal("0.01"))


class ExtractedInvoice(BaseModel):
    """Strict, versioned schema representing normalized invoice extraction."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    invoice_number: str = Field(..., description="Unique invoice identifier from supplier")
    invoice_date: date = Field(..., description="Date of invoice issuance")
    due_date: Optional[date] = Field(default=None, description="Payment due date if specified")
    
    # Vendor & Customer details
    vendor_name: str = Field(..., description="Name of the issuing supplier")
    vendor_gstin: Optional[str] = Field(default=None, description="GSTIN of supplier (15 characters in India)")
    vendor_address: Optional[str] = Field(default=None)
    
    buyer_name: Optional[str] = Field(default=None, description="Name of the buyer/customer")
    buyer_gstin: Optional[str] = Field(default=None, description="GSTIN of buyer")

    place_of_supply: Optional[str] = Field(default=None, description="Place of Supply state or code, e.g. 'Uttar Pradesh (09)'")
    place_of_supply_state_code: Optional[str] = Field(default=None, description="2-digit state code of POS, e.g. '09'")
    payment_terms: Optional[str] = Field(default=None, description="e.g. '30 days from invoice date', 'Paid via Cash'")
    is_settled_or_paid: bool = Field(default=False, description="True if marked cash paid or settled")

    currency: str = Field(default="INR", description="ISO Currency code (INR, USD, EUR)")
    invoice_type: str = Field(default="PURCHASE", description="PURCHASE or SALES")
    financial_year: Optional[str] = Field(default=None, description="e.g. FY 2026-27")
    
    # Financial Totals (Strict Decimal)
    subtotal: Decimal = Field(..., description="Sum of taxable line items before tax")
    total_discount: Decimal = Field(default=Decimal("0.00"), description="Document-level discount")
    total_tax: Decimal = Field(default=Decimal("0.00"), description="Total tax amount")
    round_off: Decimal = Field(default=Decimal("0.00"), description="Round-off adjustment")
    grand_total: Decimal = Field(..., description="Final invoice payable amount")

    # Line items & taxes
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    taxes: List[TaxBreakdown] = Field(default_factory=list)

    # Extraction Provenance & Quality
    confidence: ExtractionConfidence = Field(default=ExtractionConfidence.MEDIUM)
    is_date_fallback: bool = Field(default=False, description="True if invoice date could not be parsed from document and was defaulted")
    validation_flags: List[str] = Field(default_factory=list, description="Warnings or issues detected by heuristics")

    @field_validator("subtotal", "total_discount", "total_tax", "round_off", "grand_total", mode="before")
    @classmethod
    def parse_to_decimal(cls, v):
        if v is None:
            return Decimal("0.00")
        return Decimal(str(v)).quantize(Decimal("0.01"))
