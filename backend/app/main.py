import os
import shutil
import uuid
import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db.session import engine, Base, get_db
from app.models.accounting import (
    Tenant,
    Account,
    Document,
    Invoice,
    LineItem,
    JournalEntry,
    JournalLine,
    AuditLog,
    DocumentStatus,
    EntryPostingStatus,
    PeriodLock,
    BankTransaction,
    Gstr2bEntry,
)
from app.db.seed_accounts import seed_standard_accounts
from app.schemas.accounting import ProposedJournalEntry, ProposedJournalLine, EntryType, TransactionType
from app.schemas.invoice import ExtractedInvoice, InvoiceLineItem
from app.engine.ingestion import DocumentIngestionService
from app.engine.interpreter import AccountingInterpreter, get_financial_year
from app.engine.invariants import run_comprehensive_validation
from app.engine.ledger import post_journal_entry, generate_trial_balance, post_settlement_entry
from app.engine.statements import FinancialStatementService
from app.engine.bank_reconciliation import BankReconciliationService
from app.engine.gst_reconciliation import GstReconciliationService

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Ensure backwards-compatible columns for SQLite if running on pre-existing db
try:
    with engine.connect() as conn:
        from sqlalchemy import text
        res = conn.execute(text("PRAGMA table_info(tenants)"))
        cols = [r[1] for r in res.fetchall()]
        if cols and "business_type" not in cols:
            conn.execute(text("ALTER TABLE tenants ADD COLUMN business_type VARCHAR(50) DEFAULT 'SERVICES'"))
            conn.commit()

        res_d = conn.execute(text("PRAGMA table_info(documents)"))
        d_cols = [r[1] for r in res_d.fetchall()]
        if d_cols and "file_hash" not in d_cols:
            conn.execute(text("ALTER TABLE documents ADD COLUMN file_hash VARCHAR(64)"))
            conn.commit()

        res_a = conn.execute(text("PRAGMA table_info(audit_logs)"))
        a_cols = [r[1] for r in res_a.fetchall()]
        if a_cols and "user_role" not in a_cols:
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN user_role VARCHAR(50) DEFAULT 'MAKER'"))
            conn.commit()
        if a_cols and "previous_state" not in a_cols:
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN previous_state TEXT"))
            conn.commit()
        if a_cols and "new_state" not in a_cols:
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN new_state TEXT"))
            conn.commit()
except Exception:
    pass

app = FastAPI(
    title="AI-Powered Accounting Automation System",
    description="End-to-End Multimodal Invoice Intelligence & Verified Double-Entry Accounting",
    version="1.0.0",
)

# Enable CORS for Frontend React Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_invoices"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_or_create_default_tenant(db: Session) -> Tenant:
    tenant = db.query(Tenant).first()
    if not tenant:
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name="Modern Tech Solutions Pvt Ltd",
            gstin="07BBBBB1111B1Z2",
            currency="INR"
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        seed_standard_accounts(db, tenant.id)
    else:
        # Idempotently seed any newly added standard accounts into the existing tenant's COA
        seed_standard_accounts(db, tenant.id)
    return tenant


def assert_period_not_locked(db: Session, tenant_id: str, entry_date: date):
    """
    Statutory Close & Period Lock Enforcer.
    Prevents back-dated modifications, postings, or settlements into closed financial periods.
    Checks both specific month lock (e.g. '2026-10') and full financial year lock (e.g. 'FY 2026-27').
    """
    month_key = entry_date.strftime("%Y-%m")
    fy_key = get_financial_year(entry_date)

    lock = db.query(PeriodLock).filter(
        PeriodLock.tenant_id == tenant_id,
        PeriodLock.is_locked == True,
        PeriodLock.period_key.in_([month_key, fy_key])
    ).first()
    if lock:
        raise HTTPException(
            status_code=423,  # 423 Locked
            detail=f"Statutory Period Lock: Financial period '{lock.period_key}' is locked (locked by {lock.locked_by or 'Firm Admin'}). Direct voucher postings, modifications, or settlements are prohibited. Reason: {lock.lock_reason or 'Closed accounting period'}."
        )



@app.get("/api/health")
def health_check():
    return {"status": "ok", "system": "AI-Powered Accounting Automation Engine", "version": "1.0.0"}


@app.get("/api/tenant")
def get_tenant_info(db: Session = Depends(get_db)):
    tenant = get_or_create_default_tenant(db)
    return {
        "id": tenant.id,
        "name": tenant.name,
        "gstin": tenant.gstin,
        "currency": tenant.currency,
        "business_type": getattr(tenant, "business_type", "IT_SERVICES")
    }


@app.put("/api/tenant/business-type")
def update_tenant_business_type(payload: dict, db: Session = Depends(get_db)):
    tenant = get_or_create_default_tenant(db)
    new_type = payload.get("business_type", "IT_SERVICES")
    tenant.business_type = new_type
    db.commit()
    db.refresh(tenant)
    return {
        "status": "ok",
        "business_type": tenant.business_type,
        "message": f"Entity commercial profile updated to {tenant.business_type}"
    }


@app.put("/api/tenant/profile")
def update_tenant_profile(payload: dict, db: Session = Depends(get_db)):
    """Allows full configuration of entity name, GSTIN, business type, and currency during login/setup."""
    tenant = get_or_create_default_tenant(db)
    if "name" in payload and payload["name"]:
        tenant.name = payload["name"].strip()
    if "gstin" in payload and payload["gstin"]:
        tenant.gstin = payload["gstin"].strip()
    if "business_type" in payload and payload["business_type"]:
        tenant.business_type = payload["business_type"].strip()
    if "currency" in payload and payload["currency"]:
        tenant.currency = payload["currency"].strip()
    db.commit()
    db.refresh(tenant)
    return {
        "status": "ok",
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "gstin": tenant.gstin,
            "business_type": tenant.business_type,
            "currency": tenant.currency
        }
    }


@app.get("/api/accounts")
def list_accounts(db: Session = Depends(get_db)):
    tenant = get_or_create_default_tenant(db)
    accounts = db.query(Account).filter(Account.tenant_id == tenant.id, Account.is_active == True).order_by(Account.code).all()
    return [
        {
            "id": a.id,
            "code": a.code,
            "name": a.name,
            "category": a.category.value,
            "normal_balance": a.normal_balance.value
        }
        for a in accounts
    ]


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    tenant = get_or_create_default_tenant(db)
    file_bytes = await file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Duplicate file hash check
    existing_doc = db.query(Document).filter(Document.tenant_id == tenant.id, Document.file_hash == file_hash).first()
    if existing_doc:
        raise HTTPException(
            status_code=400,
            detail=f"Duplicate file detected: Document '{existing_doc.filename}' with identical SHA-256 hash has already been uploaded."
        )

    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    doc = Document(
        id=file_id,
        tenant_id=tenant.id,
        filename=file.filename,
        file_path=file_path,
        mime_type=file.content_type or "application/pdf",
        file_hash=file_hash,
        status=DocumentStatus.UPLOADED
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {"document_id": doc.id, "filename": doc.filename, "status": doc.status, "file_hash": file_hash}


@app.post("/api/documents/upload-batch")
async def upload_documents_batch(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    tenant = get_or_create_default_tenant(db)
    uploaded = []
    skipped = []

    for file in files:
        file_bytes = await file.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Check duplicate
        existing_doc = db.query(Document).filter(Document.tenant_id == tenant.id, Document.file_hash == file_hash).first()
        if existing_doc:
            skipped.append({"filename": file.filename, "reason": "Duplicate file (matching SHA-256 hash)"})
            continue

        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)

        doc = Document(
            id=file_id,
            tenant_id=tenant.id,
            filename=file.filename,
            file_path=file_path,
            mime_type=file.content_type or "application/pdf",
            file_hash=file_hash,
            status=DocumentStatus.UPLOADED
        )
        db.add(doc)
        uploaded.append({"document_id": doc.id, "filename": doc.filename, "status": doc.status})

    db.commit()
    return {"count": len(uploaded), "documents": uploaded, "skipped": skipped}


@app.get("/api/documents")
def list_documents(db: Session = Depends(get_db)):
    tenant = get_or_create_default_tenant(db)
    docs = db.query(Document).filter(Document.tenant_id == tenant.id).order_by(Document.uploaded_at.desc()).all()
    
    results = []
    for d in docs:
        inv = d.invoice
        results.append({
            "id": d.id,
            "filename": d.filename,
            "status": d.status,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            "invoice_number": inv.invoice_number if inv else None,
            "invoice_date": inv.invoice_date.isoformat() if inv and inv.invoice_date else None,
            "due_date": inv.due_date.isoformat() if inv and inv.due_date else None,
            "vendor_name": inv.vendor_name if inv else None,
            "buyer_name": inv.buyer_name if inv else None,
            "grand_total": float(inv.grand_total) if inv else None,
            "invoice_type": getattr(inv, "invoice_type", "PURCHASE") if inv else "PURCHASE",
            "payment_status": getattr(inv, "payment_status", "UNPAID") if inv else "UNPAID",
            "amount_paid": float(getattr(inv, "amount_paid", 0.0)) if inv else 0.0,
            "financial_year": getattr(inv, "financial_year", None) if inv else None
        })
    return results


@app.post("/api/documents/{doc_id}/process")
def process_document(doc_id: str, direction: Optional[str] = None, db: Session = Depends(get_db)):
    tenant = get_or_create_default_tenant(db)
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == tenant.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # 1. Run Ingestion, Table Layout Correction & Heuristics
    try:
        extracted = DocumentIngestionService.process_pdf_invoice(doc.file_path)
    except Exception as e:
        doc.status = DocumentStatus.REVIEW_REQUIRED
        db.commit()
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    # Auto-detect invoice direction (Purchase vs Sales) if not specified
    if not direction:
        is_sales = False
        if extracted.vendor_gstin and tenant.gstin and extracted.vendor_gstin.upper() == tenant.gstin.upper():
            is_sales = True
        elif tenant.name and extracted.vendor_name and (tenant.name.lower() in extracted.vendor_name.lower() or extracted.vendor_name.lower() in tenant.name.lower()):
            is_sales = True
        direction = "SALES" if is_sales else "PURCHASE"

    fy = get_financial_year(extracted.invoice_date)

    # 2. Persist Extracted Invoice
    existing_inv = db.query(Invoice).filter(Invoice.document_id == doc.id).first()
    if existing_inv:
        db.delete(existing_inv)
        db.flush()

    db_invoice = Invoice(
        document_id=doc.id,
        tenant_id=tenant.id,
        invoice_number=extracted.invoice_number,
        invoice_date=extracted.invoice_date,
        due_date=extracted.due_date,
        vendor_name=extracted.vendor_name,
        vendor_gstin=extracted.vendor_gstin,
        buyer_name=extracted.buyer_name,
        buyer_gstin=extracted.buyer_gstin,
        subtotal=extracted.subtotal,
        total_tax=extracted.total_tax,
        total_discount=extracted.total_discount,
        grand_total=extracted.grand_total,
        invoice_type=direction,
        payment_status="UNPAID",
        amount_paid=Decimal("0.00"),
        financial_year=fy,
        validation_flags="; ".join(extracted.validation_flags) if extracted.validation_flags else None
    )
    db.add(db_invoice)
    db.flush()

    for item in extracted.line_items:
        db_item = LineItem(
            invoice_id=db_invoice.id,
            description=item.description,
            hsn_sac=item.hsn_sac,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_amount=item.discount_amount,
            total_amount=item.total_amount
        )
        db.add(db_item)

    # 3. Interpret Transaction and Generate Journal Proposal
    proposal = AccountingInterpreter.interpret_invoice(
        invoice=extracted,
        document_id=doc.id,
        creditor_account_code="2010",
        business_type=getattr(tenant, "business_type", "IT_SERVICES"),
        invoice_direction=direction
    )

    # 4. Run Multi-Stage Deterministic Validation Suite
    active_codes = {acc.code for acc in db.query(Account).filter(Account.tenant_id == tenant.id, Account.is_active == True).all()}
    validation_report = run_comprehensive_validation(
        invoice=extracted,
        entry=proposal,
        active_account_codes=active_codes
    )
    proposal.validation_report = validation_report

    doc.status = DocumentStatus.REVIEW_REQUIRED if (validation_report.has_blocking_failures or not validation_report.can_post_automatically) else DocumentStatus.PROCESSED
    db.commit()

    return {
        "status": doc.status,
        "extracted_invoice": extracted.model_dump(),
        "proposed_journal_entry": proposal.model_dump(),
        "validation_report": validation_report.model_dump()
    }


@app.post("/api/documents/batch-process")
def batch_process_pending_documents(db: Session = Depends(get_db)):
    """Processes all newly uploaded documents in batch mode."""
    tenant = get_or_create_default_tenant(db)
    pending_docs = (
        db.query(Document)
        .filter(Document.tenant_id == tenant.id, Document.status == DocumentStatus.UPLOADED)
        .all()
    )

    results = []
    for doc in pending_docs:
        try:
            res = process_document(doc.id, db=db)
            results.append({"document_id": doc.id, "filename": doc.filename, "status": res["status"]})
        except Exception as e:
            results.append({"document_id": doc.id, "filename": doc.filename, "status": "ERROR", "error": str(e)})

    return {"processed_count": len(results), "results": results}


@app.get("/api/documents/{doc_id}")
def get_document_details(doc_id: str, db: Session = Depends(get_db)):
    tenant = get_or_create_default_tenant(db)
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == tenant.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    inv = doc.invoice
    inv_data = None
    proposal_data = None

    if inv:
        line_items_data = [
            {
                "description": it.description,
                "hsn_sac": it.hsn_sac,
                "quantity": float(it.quantity),
                "unit_price": float(it.unit_price),
                "discount_amount": float(it.discount_amount),
                "total_amount": float(it.total_amount)
            }
            for it in inv.line_items
        ]
        inv_data = {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date.isoformat(),
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "vendor_name": inv.vendor_name,
            "vendor_gstin": inv.vendor_gstin,
            "buyer_name": inv.buyer_name,
            "buyer_gstin": inv.buyer_gstin,
            "subtotal": float(inv.subtotal),
            "total_tax": float(inv.total_tax),
            "total_discount": float(inv.total_discount),
            "grand_total": float(inv.grand_total),
            "invoice_type": getattr(inv, "invoice_type", "PURCHASE"),
            "payment_status": getattr(inv, "payment_status", "UNPAID"),
            "amount_paid": float(getattr(inv, "amount_paid", 0.0)),
            "financial_year": getattr(inv, "financial_year", None),
            "validation_flags": inv.validation_flags.split("; ") if inv.validation_flags else [],
            "line_items": line_items_data
        }

        # Re-generate proposal and validation report based on current (including user-edited) invoice values
        items_schema = [
            InvoiceLineItem(
                description=it.description,
                hsn_sac=it.hsn_sac,
                quantity=it.quantity,
                unit_price=it.unit_price,
                discount_amount=it.discount_amount,
                total_amount=it.total_amount
            )
            for it in inv.line_items
        ]
        extracted_obj = ExtractedInvoice(
            invoice_number=inv.invoice_number,
            invoice_date=inv.invoice_date,
            due_date=inv.due_date,
            vendor_name=inv.vendor_name,
            vendor_gstin=inv.vendor_gstin,
            buyer_name=inv.buyer_name,
            buyer_gstin=inv.buyer_gstin,
            subtotal=inv.subtotal,
            total_tax=inv.total_tax,
            total_discount=inv.total_discount,
            grand_total=inv.grand_total,
            line_items=items_schema
        )
        proposal = AccountingInterpreter.interpret_invoice(
            extracted_obj,
            document_id=doc.id,
            business_type=getattr(tenant, "business_type", "IT_SERVICES"),
            invoice_direction=getattr(inv, "invoice_type", "PURCHASE")
        )
        active_codes = {acc.code for acc in db.query(Account).filter(Account.tenant_id == tenant.id, Account.is_active == True).all()}
        validation_report = run_comprehensive_validation(
            invoice=extracted_obj,
            entry=proposal,
            active_account_codes=active_codes
        )
        proposal.validation_report = validation_report
        proposal_data = proposal.model_dump()
        validation_data = validation_report.model_dump()

    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "invoice": inv_data,
        "proposal": proposal_data,
        "validation_report": validation_data if inv else None
    }


@app.put("/api/documents/{doc_id}/invoice")
def update_invoice_details(doc_id: str, payload: dict, db: Session = Depends(get_db)):
    """Allows user to edit and correct extracted invoice data directly before approving."""
    tenant = get_or_create_default_tenant(db)
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == tenant.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Statutory Ledger Immutability Gate 1: Document posting status
    if doc.status == DocumentStatus.POSTED:
        raise HTTPException(
            status_code=409,
            detail="Statutory ledger immutability: Cannot modify invoice details after document has been posted to the general ledger. Direct mutation breaks source-to-ledger audit trails. Create a contra reversal (/api/journal/reverse/{entry_id}) or adjustment voucher instead."
        )

    inv = doc.invoice
    if not inv:
        raise HTTPException(status_code=400, detail="No extracted invoice exists for this document yet.")

    # Statutory Ledger Immutability Gate 2: Associated posted journal entry
    posted_entry = db.query(JournalEntry).filter(
        JournalEntry.invoice_id == inv.id,
        JournalEntry.status == EntryPostingStatus.POSTED
    ).first()
    if posted_entry:
        raise HTTPException(
            status_code=409,
            detail=f"Statutory ledger immutability: Invoice #{inv.invoice_number} is already posted to general ledger (Entry ID: {posted_entry.id}). Direct edits are strictly prohibited to maintain source-to-ledger audit integrity."
        )

    # Statutory Period Lock Gate
    if inv.invoice_date:
        assert_period_not_locked(db, tenant.id, inv.invoice_date)

    # Capture snapshot before mutation for immutable audit trail
    prev_snapshot = {
        "invoice_number": inv.invoice_number,
        "vendor_name": inv.vendor_name,
        "vendor_gstin": inv.vendor_gstin,
        "subtotal": str(inv.subtotal),
        "total_tax": str(inv.total_tax),
        "grand_total": str(inv.grand_total),
        "line_items_count": len(inv.line_items)
    }

    # Update basic metadata
    if "invoice_number" in payload and payload["invoice_number"]:
        inv.invoice_number = payload["invoice_number"].strip()
    if "invoice_date" in payload and payload["invoice_date"]:
        inv.invoice_date = date.fromisoformat(payload["invoice_date"])
        inv.financial_year = get_financial_year(inv.invoice_date)
    if "due_date" in payload:
        inv.due_date = date.fromisoformat(payload["due_date"]) if payload["due_date"] else None
    if "vendor_name" in payload and payload["vendor_name"]:
        inv.vendor_name = payload["vendor_name"].strip()
    if "vendor_gstin" in payload:
        inv.vendor_gstin = payload["vendor_gstin"].strip() if payload["vendor_gstin"] else None
    if "buyer_name" in payload and payload["buyer_name"]:
        inv.buyer_name = payload["buyer_name"].strip()
    if "buyer_gstin" in payload:
        inv.buyer_gstin = payload["buyer_gstin"].strip() if payload["buyer_gstin"] else None
    if "invoice_type" in payload:
        inv.invoice_type = payload["invoice_type"]

    # Update line items if provided
    if "line_items" in payload and isinstance(payload["line_items"], list):
        db.query(LineItem).filter(LineItem.invoice_id == inv.id).delete()
        subtotal = Decimal("0.00")
        for item in payload["line_items"]:
            qty = Decimal(str(item.get("quantity", 1)))
            uprice = Decimal(str(item.get("unit_price", 0)))
            disc = Decimal(str(item.get("discount_amount", 0)))
            tot = Decimal(str(item.get("total_amount", (qty * uprice) - disc)))
            subtotal += tot
            db_item = LineItem(
                invoice_id=inv.id,
                description=item.get("description", "Item"),
                hsn_sac=item.get("hsn_sac"),
                quantity=qty,
                unit_price=uprice,
                discount_amount=disc,
                total_amount=tot
            )
            db.add(db_item)
        inv.subtotal = subtotal

    if "total_tax" in payload:
        inv.total_tax = Decimal(str(payload["total_tax"]))
    if "grand_total" in payload:
        inv.grand_total = Decimal(str(payload["grand_total"]))
    else:
        inv.grand_total = inv.subtotal + inv.total_tax

    db.commit()
    db.refresh(inv)

    # Re-run interpreter and validation suite with updated values
    items_schema = [
        InvoiceLineItem(
            description=li.description,
            hsn_sac=li.hsn_sac,
            quantity=li.quantity,
            unit_price=li.unit_price,
            discount_amount=li.discount_amount,
            total_amount=li.total_amount
        )
        for li in inv.line_items
    ]
    extracted_obj = ExtractedInvoice(
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        vendor_name=inv.vendor_name,
        vendor_gstin=inv.vendor_gstin,
        buyer_name=inv.buyer_name,
        buyer_gstin=inv.buyer_gstin,
        subtotal=inv.subtotal,
        total_tax=inv.total_tax,
        total_discount=inv.total_discount,
        grand_total=inv.grand_total,
        line_items=items_schema
    )

    proposal = AccountingInterpreter.interpret_invoice(
        extracted_obj,
        document_id=doc.id,
        business_type=getattr(tenant, "business_type", "IT_SERVICES"),
        invoice_direction=inv.invoice_type
    )
    active_codes = {acc.code for acc in db.query(Account).filter(Account.tenant_id == tenant.id, Account.is_active == True).all()}
    validation_report = run_comprehensive_validation(
        invoice=extracted_obj,
        entry=proposal,
        active_account_codes=active_codes
    )
    doc.status = DocumentStatus.REVIEW_REQUIRED if (validation_report.has_blocking_failures or not validation_report.can_post_automatically) else DocumentStatus.PROCESSED

    # Immutable audit log with before/after state
    new_snapshot = {
        "invoice_number": inv.invoice_number,
        "vendor_name": inv.vendor_name,
        "vendor_gstin": inv.vendor_gstin,
        "subtotal": str(inv.subtotal),
        "total_tax": str(inv.total_tax),
        "grand_total": str(inv.grand_total),
        "line_items_count": len(inv.line_items)
    }
    audit_entry = AuditLog(
        tenant_id=tenant.id,
        entity_name="Invoice",
        entity_id=inv.id,
        action="EDIT",
        performed_by=payload.get("edited_by", "MAKER_ACCOUNTANT"),
        user_role=payload.get("user_role", "MAKER"),
        previous_state=json.dumps(prev_snapshot),
        new_state=json.dumps(new_snapshot),
        details=f"Invoice #{inv.invoice_number} voucher fields updated and re-verified against accounting invariants."
    )
    db.add(audit_entry)
    db.commit()

    return {
        "status": "ok",
        "message": "Invoice details updated successfully and verified.",
        "doc_status": doc.status,
        "invoice_id": inv.id,
        "proposal": proposal.model_dump(),
        "validation_report": validation_report.model_dump()
    }


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """Deletes an unposted invoice document. Posted documents cannot be deleted and require accounting reversal."""
    tenant = get_or_create_default_tenant(db)
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == tenant.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Invariant: Statutory ledger immutability
    if doc.status == DocumentStatus.POSTED:
        raise HTTPException(
            status_code=400,
            detail="Statutory ledger immutability: Posted documents cannot be deleted. Use the reversal endpoint (/api/journal/reverse/{entry_id}) to generate an opposite contra journal entry."
        )

    if doc.invoice:
        # Check if there are any posted journal entries
        has_posted = db.query(JournalEntry).filter(
            JournalEntry.invoice_id == doc.invoice.id,
            JournalEntry.status == EntryPostingStatus.POSTED
        ).first()
        if has_posted:
            raise HTTPException(
                status_code=400,
                detail="Statutory ledger immutability: Cannot delete invoice with posted journal entries. Execute a reversal entry instead."
            )

        # Delete any draft line items
        db.query(LineItem).filter(LineItem.invoice_id == doc.invoice.id).delete(synchronize_session=False)
        db.delete(doc.invoice)

    db.delete(doc)
    db.commit()
    return {"status": "ok", "message": f"Document {doc.filename} removed successfully."}


@app.post("/api/documents/reset-data")
def reset_all_data(
    force: bool = False,
    user_role: Optional[str] = Header(None, alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    """
    Clears sample invoices, documents, and journals for testing.
    Protects locked periods and immutable audit logs unless explicitly authorized by an admin.
    """
    tenant = get_or_create_default_tenant(db)

    # Check if any active period locks exist
    active_locks = db.query(PeriodLock).filter(
        PeriodLock.tenant_id == tenant.id,
        PeriodLock.is_locked == True
    ).all()

    if active_locks and not force:
        locked_keys = [l.period_key for l in active_locks]
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reset workspace: Accounting periods {locked_keys} are currently locked. Unlock them first or specify force=True with administrative credentials."
        )

    # 1. Delete journal lines and entries
    entry_ids = [e.id for e in db.query(JournalEntry.id).filter(JournalEntry.tenant_id == tenant.id).all()]
    if entry_ids:
        db.query(JournalLine).filter(JournalLine.entry_id.in_(entry_ids)).delete(synchronize_session=False)
        db.query(JournalEntry).filter(JournalEntry.tenant_id == tenant.id).delete(synchronize_session=False)

    # 2. Delete line items and invoices
    inv_ids = [i.id for i in db.query(Invoice.id).filter(Invoice.tenant_id == tenant.id).all()]
    if inv_ids:
        db.query(LineItem).filter(LineItem.invoice_id.in_(inv_ids)).delete(synchronize_session=False)
        db.query(Invoice).filter(Invoice.tenant_id == tenant.id).delete(synchronize_session=False)

    # 3. Delete documents
    db.query(Document).filter(Document.tenant_id == tenant.id).delete(synchronize_session=False)

    # 4. Only delete audit logs if force is explicitly passed with FIRM_ADMIN role
    effective_role = (user_role or "USER").upper()
    if force and effective_role in {"FIRM_ADMIN", "ADMIN"}:
        db.query(AuditLog).filter(AuditLog.tenant_id == tenant.id).delete(synchronize_session=False)
        db.query(PeriodLock).filter(PeriodLock.tenant_id == tenant.id).delete(synchronize_session=False)

    db.commit()
    return {"status": "ok", "message": "All invoice records and ledgers cleared successfully. Audit trails and period locks preserved."}


@app.post("/api/journal/post")
def post_entry(
    proposal: ProposedJournalEntry,
    posted_by: Optional[str] = "AUDIT_CHECKER",
    user_role: Optional[str] = Header(None, alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    tenant = get_or_create_default_tenant(db)
    try:
        # 1. Locate source invoice if exists
        inv = None
        if proposal.source_document_id:
            inv = db.query(Invoice).filter(Invoice.document_id == proposal.source_document_id).first()
        if not inv and proposal.invoice_number:
            inv = db.query(Invoice).filter(Invoice.tenant_id == tenant.id, Invoice.invoice_number == proposal.invoice_number).first()

        # Check Period Lock
        entry_date = proposal.entry_date or (inv.invoice_date if inv else date.today())
        assert_period_not_locked(db, tenant.id, entry_date)

        effective_role = (user_role or "CHECKER").upper()
        authorized_reviewers = {"AUDIT_CHECKER", "MAKER_CHECKER_REVIEWER", "ACCOUNTANT_REVIEWER", "FIRM_ADMIN", "SENIOR_ACCOUNTANT"}
        authorized_roles = {"CHECKER", "AUDITOR", "ADMIN", "FIRM_ADMIN", "SENIOR_ACCOUNTANT"}

        # 2. Server-side authoritative validation against stored voucher
        if inv:
            # Check duplicate posting
            already_posted = db.query(JournalEntry).filter(
                JournalEntry.invoice_id == inv.id,
                JournalEntry.status == EntryPostingStatus.POSTED
            ).first()
            if already_posted:
                raise HTTPException(
                    status_code=409,
                    detail=f"Statutory ledger immutability: Invoice #{inv.invoice_number} has already been posted to the general ledger (Journal Entry #{already_posted.id}). Duplicate posting is blocked."
                )

            # Maker-Checker strict separation:
            # If document was created/uploaded by a specific maker, the checker approving it must be authorized
            # and non-checker roles (e.g. MAKER / CLERK) cannot self-approve vouchers requiring human review.
            is_authorized_checker = (posted_by in authorized_reviewers) or (effective_role in authorized_roles)

            # Re-generate authoritative proposal from stored source voucher
            items_schema = [
                InvoiceLineItem(
                    description=li.description,
                    hsn_sac=li.hsn_sac,
                    quantity=li.quantity,
                    unit_price=li.unit_price,
                    discount_amount=li.discount_amount,
                    total_amount=li.total_amount
                )
                for li in inv.line_items
            ]
            source_invoice = ExtractedInvoice(
                invoice_number=inv.invoice_number,
                invoice_date=inv.invoice_date,
                due_date=inv.due_date,
                vendor_name=inv.vendor_name,
                vendor_gstin=inv.vendor_gstin,
                buyer_name=inv.buyer_name,
                buyer_gstin=inv.buyer_gstin,
                subtotal=inv.subtotal,
                total_tax=inv.total_tax,
                total_discount=inv.total_discount,
                grand_total=inv.grand_total,
                line_items=items_schema
            )
            authoritative_proposal = AccountingInterpreter.interpret_invoice(
                source_invoice,
                document_id=proposal.source_document_id or (inv.document.id if inv.document else None),
                business_type=getattr(tenant, "business_type", "IT_SERVICES"),
                invoice_direction=inv.invoice_type
            )

            # Invariant check: Verify client proposal amount does not deviate from approved source voucher
            if abs(proposal.total_debits - authoritative_proposal.total_debits) > Decimal("0.05") or \
               abs(proposal.total_credits - authoritative_proposal.total_credits) > Decimal("0.05"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Voucher integrity violation: Client journal proposal amount (Debits: {proposal.total_debits}) does not match server-verified source voucher total ({authoritative_proposal.total_debits})."
                )

            # Maker-Checker Authorization Gate:
            # If review is required, verify caller has approver/reviewer privileges
            if authoritative_proposal.requires_human_review and not is_authorized_checker:
                raise HTTPException(
                    status_code=403,
                    detail=f"Maker-Checker Authorization Required: Proposal for invoice #{proposal.invoice_number} requires review ({'; '.join(authoritative_proposal.review_reasons)}). Caller '{posted_by}' with role '{effective_role}' is not authorized to approve."
                )

            entry_to_post = proposal if (proposal.is_balanced and abs(proposal.total_debits - inv.grand_total) <= Decimal("0.05")) else authoritative_proposal

            posted = post_journal_entry(
                db,
                tenant.id,
                entry_to_post,
                posted_by=posted_by or "AUDIT_CHECKER",
                allow_review_override=bool(is_authorized_checker),
                invoice_id=inv.id
            )
        else:
            # Standalone or manual journal entry without pre-existing source invoice
            is_authorized_checker = (posted_by in authorized_reviewers) or (effective_role in authorized_roles)
            if proposal.requires_human_review and not is_authorized_checker:
                raise HTTPException(
                    status_code=403,
                    detail=f"Maker-Checker Authorization Required: Manual entry requires human review. Caller '{posted_by}' with role '{effective_role}' is not authorized to approve."
                )

            posted = post_journal_entry(
                db,
                tenant.id,
                proposal,
                posted_by=posted_by or "AUDIT_CHECKER",
                allow_review_override=bool(is_authorized_checker),
                invoice_id=None
            )

        # Update linked document status
        if proposal.source_document_id:
            doc = db.query(Document).filter(Document.id == proposal.source_document_id).first()
            if doc:
                doc.status = DocumentStatus.POSTED
                db.commit()

        return {"status": "SUCCESS", "journal_entry_id": posted.id, "invoice_number": posted.invoice_number}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/journal/reverse/{entry_id}")
def reverse_journal_entry(entry_id: str, payload: Optional[dict] = None, db: Session = Depends(get_db)):
    """
    Executes a GAAP / Ind AS statutory reversal of a posted journal entry.
    Instead of mutating or deleting historic ledgers, an opposite contra entry is created and posted.
    """
    tenant = get_or_create_default_tenant(db)
    original_entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id,
        JournalEntry.tenant_id == tenant.id
    ).first()

    if not original_entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if original_entry.status != EntryPostingStatus.POSTED:
        raise HTTPException(status_code=400, detail="Only POSTED journal entries can be reversed")

    # Check if already reversed
    existing_reversal = db.query(JournalEntry).filter(
        JournalEntry.tenant_id == tenant.id,
        JournalEntry.narration.like(f"%Reversal of Journal Entry #{entry_id}%")
    ).first()
    if existing_reversal:
        raise HTTPException(status_code=400, detail=f"Entry has already been reversed by Entry ID: {existing_reversal.id}")

    reason = (payload or {}).get("reason", "Administrative correction or cancellation")
    checker_name = (payload or {}).get("reversed_by", "AUDIT_CHECKER")

    # Build inverse lines: Debits become Credits, Credits become Debits
    contra_lines = []
    tot_debits = Decimal("0.00")
    tot_credits = Decimal("0.00")

    for line in original_entry.lines:
        inv_type = EntryType.CREDIT if line.entry_type == EntryType.DEBIT else EntryType.DEBIT
        amt = Decimal(str(line.amount)).quantize(Decimal("0.01"))
        if inv_type == EntryType.DEBIT:
            tot_debits += amt
        else:
            tot_credits += amt

        contra_lines.append(ProposedJournalLine(
            account_code=line.account.code,
            account_name=line.account.name,
            entry_type=inv_type,
            amount=amt,
            description=f"Reversal: {line.description or 'Contra line'}"
        ))

    linked_inv = db.query(Invoice).filter(Invoice.id == original_entry.invoice_id).first() if original_entry.invoice_id else None
    doc_id = original_entry.document_id or (linked_inv.document_id if linked_inv else None)

    reversal_proposal = ProposedJournalEntry(
        invoice_number=f"REV-{original_entry.invoice_number}",
        source_document_id=doc_id,
        transaction_type=TransactionType.REVERSAL,
        entry_date=date.today(),
        narration=f"Reversal of Journal Entry #{entry_id} (Ref: {original_entry.invoice_number}). Reason: {reason}",
        reasoning=f"Statutory contra reversal of #{entry_id}: {reason}",
        lines=contra_lines,
        total_debits=tot_debits,
        total_credits=tot_credits,
        is_balanced=(tot_debits == tot_credits),
        applied_rules=[f"Statutory Reversal Protocol for Entry {entry_id}", f"Reason: {reason}"]
    )

    reversal_entry = post_journal_entry(
        db=db,
        tenant_id=tenant.id,
        proposal=reversal_proposal,
        posted_by=checker_name,
        allow_review_override=True,
        invoice_id=original_entry.invoice_id
    )

    # Mark invoice as cancelled/reversed if present
    if linked_inv:
        linked_inv.payment_status = "REVERSED"
        db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Entry #{entry_id} successfully reversed by Contra Entry #{reversal_entry.id}.",
        "reversal_entry_id": reversal_entry.id,
        "invoice_number": reversal_entry.invoice_number
    }


@app.post("/api/invoices/{invoice_id}/settle")
def settle_invoice_payment(invoice_id: str, payload: dict, db: Session = Depends(get_db)):
    tenant = get_or_create_default_tenant(db)
    payment_account_code = payload.get("payment_account_code", "1020")
    payment_ref = payload.get("payment_reference", f"TXN-{uuid.uuid4().hex[:8].upper()}")
    amount_val = payload.get("amount")
    amount = Decimal(str(amount_val)) if amount_val is not None else None
    pay_date_str = payload.get("payment_date")
    pay_date = date.fromisoformat(pay_date_str) if pay_date_str else date.today()

    # Enforce period lock on settlements
    assert_period_not_locked(db, tenant.id, pay_date)

    try:
        entry = post_settlement_entry(
            db=db,
            tenant_id=tenant.id,
            invoice_id=invoice_id,
            payment_account_code=payment_account_code,
            payment_date=pay_date,
            amount=amount,
            payment_reference=payment_ref,
            posted_by="USER_SETTLEMENT"
        )
        return {
            "status": "SUCCESS",
            "journal_entry_id": entry.id,
            "invoice_number": entry.invoice_number,
            "payment_reference": entry.payment_reference,
            "message": f"Settlement posted successfully to General Ledger (Entry #{entry.invoice_number})"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/financial-years")
def list_financial_years(db: Session = Depends(get_db)):
    tenant = get_or_create_default_tenant(db)
    # Collect distinct FYs from posted entries and invoices
    fys_entries = {r[0] for r in db.query(JournalEntry.financial_year).filter(JournalEntry.tenant_id == tenant.id, JournalEntry.financial_year.isnot(None)).distinct().all()}
    fys_invoices = {r[0] for r in db.query(Invoice.financial_year).filter(Invoice.tenant_id == tenant.id, Invoice.financial_year.isnot(None)).distinct().all()}
    current_fy = get_financial_year(date.today())
    all_fys = sorted(list(fys_entries.union(fys_invoices).union({current_fy, "FY 2026-27"})), reverse=True)
    return {"current_financial_year": current_fy, "available_financial_years": all_fys}


@app.get("/api/reports/ledger")
def get_general_ledger(
    financial_year: Optional[str] = None,
    as_of_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    tenant = get_or_create_default_tenant(db)
    query = (
        db.query(JournalEntry)
        .filter(JournalEntry.tenant_id == tenant.id, JournalEntry.status == EntryPostingStatus.POSTED)
    )
    if financial_year:
        query = query.filter(JournalEntry.financial_year == financial_year)
    if as_of_date:
        query = query.filter(JournalEntry.entry_date <= date.fromisoformat(as_of_date))

    entries = query.order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc()).all()

    results = []
    for e in entries:
        lines = [
            {
                "account_code": l.account.code,
                "account_name": l.account.name,
                "entry_type": l.entry_type.value,
                "amount": float(l.amount),
                "description": l.description
            }
            for l in e.lines
        ]
        results.append({
            "id": e.id,
            "invoice_number": e.invoice_number,
            "entry_date": e.entry_date.isoformat(),
            "financial_year": e.financial_year,
            "payment_reference": e.payment_reference,
            "transaction_type": e.transaction_type.value,
            "narration": e.narration,
            "lines": lines
        })
    return results


@app.get("/api/reports/subsidiary-ledger")
def get_subsidiary_ledger(
    party_type: str = "ALL",  # ALL, VENDOR (Payables), CUSTOMER (Receivables)
    financial_year: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns Party-Level Subsidiary Ledgers for Accounts Payable (Creditors)
    and Accounts Receivable (Debtors), with running balance and settlement reconciliation.
    """
    tenant = get_or_create_default_tenant(db)
    query = db.query(Invoice).filter(Invoice.tenant_id == tenant.id)
    if financial_year:
        query = query.filter(Invoice.financial_year == financial_year)
    invoices = query.all()

    vendors: Dict[str, Any] = {}
    customers: Dict[str, Any] = {}

    for inv in invoices:
        inv_type = getattr(inv, "invoice_type", "PURCHASE")
        if inv_type == "PURCHASE":
            name = inv.vendor_name or "Unknown Vendor"
            if name not in vendors:
                vendors[name] = {
                    "party_name": name,
                    "gstin": inv.vendor_gstin,
                    "account_code": "2010",
                    "account_name": "Accounts Payable / Sundry Creditors",
                    "total_billed": Decimal("0.00"),
                    "total_paid": Decimal("0.00"),
                    "balance_due": Decimal("0.00"),
                    "invoices": []
                }
            v = vendors[name]
            v["total_billed"] += inv.grand_total
            v["total_paid"] += inv.amount_paid
            v["balance_due"] += (inv.grand_total - inv.amount_paid)
            v["invoices"].append({
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat(),
                "grand_total": float(inv.grand_total),
                "amount_paid": float(inv.amount_paid),
                "balance_due": float(inv.grand_total - inv.amount_paid),
                "payment_status": inv.payment_status,
                "financial_year": inv.financial_year
            })
        else:
            name = inv.buyer_name or "Unknown Customer"
            if name not in customers:
                customers[name] = {
                    "party_name": name,
                    "gstin": inv.buyer_gstin,
                    "account_code": "1030",
                    "account_name": "Accounts Receivable / Sundry Debtors",
                    "total_billed": Decimal("0.00"),
                    "total_received": Decimal("0.00"),
                    "balance_due": Decimal("0.00"),
                    "invoices": []
                }
            c = customers[name]
            c["total_billed"] += inv.grand_total
            c["total_received"] += inv.amount_paid
            c["balance_due"] += (inv.grand_total - inv.amount_paid)
            c["invoices"].append({
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat(),
                "grand_total": float(inv.grand_total),
                "amount_paid": float(inv.amount_paid),
                "balance_due": float(inv.grand_total - inv.amount_paid),
                "payment_status": inv.payment_status,
                "financial_year": inv.financial_year
            })

    # Convert Decimals to float
    for v in vendors.values():
        v["total_billed"] = float(v["total_billed"])
        v["total_paid"] = float(v["total_paid"])
        v["balance_due"] = float(v["balance_due"])

    for c in customers.values():
        c["total_billed"] = float(c["total_billed"])
        c["total_received"] = float(c["total_received"])
        c["balance_due"] = float(c["balance_due"])

    return {
        "payables_vendors": list(vendors.values()),
        "receivables_customers": list(customers.values()),
        "total_payables_outstanding": sum((v["balance_due"] for v in vendors.values()), 0.0),
        "total_receivables_outstanding": sum((c["balance_due"] for c in customers.values()), 0.0)
    }


@app.get("/api/reports/trial-balance")
def get_trial_balance_report(
    as_of_date: Optional[str] = None,
    financial_year: Optional[str] = None,
    db: Session = Depends(get_db)
):
    tenant = get_or_create_default_tenant(db)
    target_date = date.fromisoformat(as_of_date) if as_of_date else date.today()
    tb = generate_trial_balance(db, tenant.id, as_of_date=target_date, financial_year=financial_year)
    return {
        "as_of_date": tb.as_of_date.isoformat(),
        "financial_year": financial_year,
        "is_balanced": tb.is_balanced,
        "total_debit_balance": float(tb.total_debit_balance),
        "total_credit_balance": float(tb.total_credit_balance),
        "rows": [
            {
                "account_code": r.account_code,
                "account_name": r.account_name,
                "category": r.category,
                "total_debits": float(r.total_debits),
                "total_credits": float(r.total_credits),
                "closing_balance": float(r.closing_balance),
                "balance_type": r.balance_type
            }
            for r in tb.rows
        ]
    }


@app.get("/api/reports/profit-and-loss")
def get_profit_and_loss(
    as_of_date: Optional[str] = None,
    financial_year: Optional[str] = None,
    db: Session = Depends(get_db)
):
    tenant = get_or_create_default_tenant(db)
    target_date = date.fromisoformat(as_of_date) if as_of_date else date.today()
    pnl = FinancialStatementService.generate_profit_and_loss(
        db, tenant.id, as_of_date=target_date, financial_year=financial_year
    )
    pnl["total_revenue"] = float(pnl["total_revenue"])
    pnl["total_expenses"] = float(pnl["total_expenses"])
    pnl["net_profit"] = float(pnl["net_profit"])
    for item in pnl["revenues"]:
        item["amount"] = float(item["amount"])
    for item in pnl["expenses"]:
        item["amount"] = float(item["amount"])
    return pnl


@app.get("/api/reports/balance-sheet")
def get_balance_sheet(
    as_of_date: Optional[str] = None,
    financial_year: Optional[str] = None,
    db: Session = Depends(get_db)
):
    tenant = get_or_create_default_tenant(db)
    target_date = date.fromisoformat(as_of_date) if as_of_date else date.today()
    bs = FinancialStatementService.generate_balance_sheet(
        db, tenant.id, as_of_date=target_date, financial_year=financial_year
    )
    bs["total_assets"] = float(bs["total_assets"])
    bs["total_liabilities"] = float(bs["total_liabilities"])
    bs["total_equity"] = float(bs["total_equity"])
    bs["retained_earnings"] = float(bs["retained_earnings"])
    bs["total_liabilities_and_equity"] = float(bs["total_liabilities_and_equity"])
    for item in bs["assets"]:
        item["amount"] = float(item["amount"])
    for item in bs["liabilities"]:
        item["amount"] = float(item["amount"])
    for item in bs["equity"]:
        item["amount"] = float(item["amount"])
    return bs


@app.get("/api/reports/monthly-analytics")
def get_monthly_analytics(
    financial_year: str = "FY 2026-27",
    db: Session = Depends(get_db)
):
    tenant = get_or_create_default_tenant(db)
    analytics = FinancialStatementService.generate_monthly_analytics(
        db, tenant.id, financial_year=financial_year
    )
    return {"financial_year": financial_year, "months": analytics}


@app.get("/api/reports/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)):
    tenant = get_or_create_default_tenant(db)
    logs = db.query(AuditLog).filter(AuditLog.tenant_id == tenant.id).order_by(AuditLog.timestamp.desc()).all()
    return [
        {
            "id": l.id,
            "entity_name": l.entity_name,
            "entity_id": l.entity_id,
            "action": l.action,
            "performed_by": l.performed_by,
            "details": l.details,
            "timestamp": l.timestamp.isoformat()
        }
        for l in logs
    ]


@app.get("/api/reports/day-books")
def get_day_books(financial_year: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Returns Specialized Books of Prime Entry:
    1. Purchase Register / Purchase Book (Inward Goods/Services)
    2. Sales Register / Sales Book (Outward Billings)
    3. Cash & Bank Book (Receipts & Payments with running cash balance)
    4. General Journal Proper (Non-cash accounting vouchers)
    """
    tenant = get_or_create_default_tenant(db)

    # 1. Purchase Book
    p_query = db.query(Invoice).filter(Invoice.tenant_id == tenant.id, Invoice.invoice_type == "PURCHASE")
    if financial_year:
        p_query = p_query.filter(Invoice.financial_year == financial_year)
    purchases = p_query.order_by(Invoice.invoice_date.desc()).all()
    purchase_book = [
        {
            "id": p.id,
            "date": p.invoice_date.isoformat(),
            "invoice_number": p.invoice_number,
            "party_name": p.vendor_name,
            "gstin": p.vendor_gstin,
            "subtotal": float(p.subtotal),
            "tax": float(p.total_tax),
            "grand_total": float(p.grand_total),
            "payment_status": p.payment_status
        }
        for p in purchases
    ]

    # 2. Sales Book
    s_query = db.query(Invoice).filter(Invoice.tenant_id == tenant.id, Invoice.invoice_type == "SALES")
    if financial_year:
        s_query = s_query.filter(Invoice.financial_year == financial_year)
    sales = s_query.order_by(Invoice.invoice_date.desc()).all()
    sales_book = [
        {
            "id": s.id,
            "date": s.invoice_date.isoformat(),
            "invoice_number": s.invoice_number,
            "party_name": s.buyer_name,
            "gstin": s.buyer_gstin,
            "subtotal": float(s.subtotal),
            "tax": float(s.total_tax),
            "grand_total": float(s.grand_total),
            "payment_status": s.payment_status
        }
        for s in sales
    ]

    # 3. Cash & Bank Book
    cb_lines = (
        db.query(JournalLine)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .join(Account, JournalLine.account_id == Account.id)
        .filter(
            JournalEntry.tenant_id == tenant.id,
            JournalEntry.status == EntryPostingStatus.POSTED,
            Account.code.in_(["1010", "1020"])
        )
    )
    if financial_year:
        cb_lines = cb_lines.filter(JournalEntry.financial_year == financial_year)
    cb_results = cb_lines.order_by(JournalEntry.entry_date.asc(), JournalEntry.created_at.asc()).all()

    cash_bank_book = []
    running_cb = Decimal("0.00")
    for l in cb_results:
        amt = Decimal(str(l.amount))
        is_receipt = l.entry_type == EntryType.DEBIT
        running_cb += amt if is_receipt else -amt
        cash_bank_book.append({
            "id": l.id,
            "date": l.entry.entry_date.isoformat(),
            "account_code": l.account.code,
            "account_name": l.account.name,
            "voucher_ref": l.entry.invoice_number,
            "particulars": l.description or l.entry.narration,
            "receipt": float(amt) if is_receipt else None,
            "payment": float(amt) if not is_receipt else None,
            "running_balance": float(running_cb)
        })

    # 4. Journal Proper (Non Cash Entries)
    je_query = (
        db.query(JournalEntry)
        .filter(JournalEntry.tenant_id == tenant.id, JournalEntry.status == EntryPostingStatus.POSTED)
    )
    if financial_year:
        je_query = je_query.filter(JournalEntry.financial_year == financial_year)
    all_jes = je_query.order_by(JournalEntry.entry_date.desc()).all()
    journal_proper = [
        {
            "id": je.id,
            "invoice_number": je.invoice_number,
            "date": je.entry_date.isoformat(),
            "transaction_type": je.transaction_type.value,
            "narration": je.narration,
            "lines": [
                {
                    "account_code": l.account.code,
                    "account_name": l.account.name,
                    "entry_type": l.entry_type.value,
                    "amount": float(l.amount)
                }
                for l in je.lines
            ]
        }
        for je in all_jes
    ]

    return {
        "purchase_book": purchase_book,
        "sales_book": sales_book,
        "cash_bank_book": cash_bank_book,
        "journal_proper": journal_proper
    }


@app.get("/api/reports/trading-and-pnl")
def get_trading_and_pnl_report(
    as_of_date: Optional[str] = None,
    financial_year: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Generates Indian format Trading Account (Gross Profit) and Profit & Loss Account (Net Profit)."""
    tenant = get_or_create_default_tenant(db)
    target_date = date.fromisoformat(as_of_date) if as_of_date else date.today()
    return FinancialStatementService.generate_trading_and_pnl(
        db, tenant.id, as_of_date=target_date, financial_year=financial_year
    )


@app.get("/api/reports/ledger-folio/{account_code}")
def get_account_folio(
    account_code: str,
    financial_year: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns ledger folio statement for any specific account code."""
    tenant = get_or_create_default_tenant(db)
    return FinancialStatementService.generate_account_ledger_folio(
        db, tenant.id, account_code=account_code, financial_year=financial_year
    )


# ==============================================================================
# STATUTORY ACCOUNTING PERIOD LOCKS (P0 FIRM WORKSPACE)
# ==============================================================================

@app.get("/api/periods")
def list_accounting_periods(db: Session = Depends(get_db)):
    """Lists accounting periods and their statutory lock status."""
    tenant = get_or_create_default_tenant(db)
    locks = db.query(PeriodLock).filter(PeriodLock.tenant_id == tenant.id).order_by(PeriodLock.period_key.desc()).all()
    return [
        {
            "id": l.id,
            "period_key": l.period_key,
            "is_locked": l.is_locked,
            "locked_at": l.locked_at.isoformat() if l.locked_at else None,
            "locked_by": l.locked_by,
            "lock_reason": l.lock_reason
        }
        for l in locks
    ]


@app.post("/api/periods/lock")
def lock_accounting_period(payload: dict, db: Session = Depends(get_db)):
    """
    Statutory Month-End Lock: Freezes an accounting period (e.g. '2026-10').
    Direct voucher postings or modifications in locked periods are strictly prohibited.
    """
    tenant = get_or_create_default_tenant(db)
    period_key = payload.get("period_key")
    if not period_key:
        raise HTTPException(status_code=400, detail="period_key (e.g. '2026-10') is required")

    lock = db.query(PeriodLock).filter(
        PeriodLock.tenant_id == tenant.id,
        PeriodLock.period_key == period_key
    ).first()

    if not lock:
        lock = PeriodLock(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            period_key=period_key
        )
        db.add(lock)

    lock.is_locked = True
    lock.locked_at = datetime.now(timezone.utc)
    lock.locked_by = payload.get("locked_by", "FIRM_ADMIN")
    lock.lock_reason = payload.get("reason", "Month-end statutory close finalized")

    audit_entry = AuditLog(
        tenant_id=tenant.id,
        entity_name="PeriodLock",
        entity_id=lock.id,
        action="LOCK",
        performed_by=lock.locked_by,
        user_role="ADMIN",
        details=f"Accounting period '{period_key}' was locked. Reason: {lock.lock_reason}"
    )
    db.add(audit_entry)
    db.commit()

    return {"status": "ok", "message": f"Period {period_key} successfully locked.", "period_key": period_key, "is_locked": True}


@app.post("/api/periods/unlock")
def unlock_accounting_period(
    payload: dict,
    user_role: Optional[str] = Header(None, alias="X-User-Role"),
    db: Session = Depends(get_db)
):
    """
    Unlocks a previously locked accounting period with an audit trail.
    Requires administrative privileges (FIRM_ADMIN, PARTNER, or SENIOR_AUDITOR).
    """
    tenant = get_or_create_default_tenant(db)
    
    # Verify administrative privilege
    effective_role = (user_role or payload.get("user_role") or "CHECKER").upper()
    admin_roles = {"FIRM_ADMIN", "ADMIN", "PARTNER", "SENIOR_AUDITOR"}
    if effective_role not in admin_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Authorization failure: Role '{effective_role}' is not authorized to unlock closed financial periods. Requires one of {sorted(list(admin_roles))}."
        )

    period_key = payload.get("period_key")
    if not period_key:
        raise HTTPException(status_code=400, detail="period_key is required")

    lock = db.query(PeriodLock).filter(
        PeriodLock.tenant_id == tenant.id,
        PeriodLock.period_key == period_key
    ).first()

    if not lock or not lock.is_locked:
        return {"status": "ok", "message": f"Period {period_key} was not locked."}

    unlocked_by = payload.get("unlocked_by") or effective_role
    lock.is_locked = False
    audit_entry = AuditLog(
        tenant_id=tenant.id,
        entity_name="PeriodLock",
        entity_id=lock.id,
        action="UNLOCK",
        performed_by=unlocked_by,
        user_role=effective_role,
        details=f"Accounting period '{period_key}' was reopened by {unlocked_by} (Role: {effective_role}). Reason: {payload.get('reason', 'Administrative audit reopen')}"
    )
    db.add(audit_entry)
    db.commit()

    return {"status": "ok", "message": f"Period {period_key} unlocked.", "period_key": period_key, "is_locked": False}


# ==============================================================================
# BANK FEED IMPORT & RECONCILIATION STATEMENT (BRS) (P0 FIRM WORKSPACE)
# ==============================================================================

@app.post("/api/reconciliation/bank/upload-csv")
def upload_bank_statement_csv(payload: dict, db: Session = Depends(get_db)):
    """Imports bank statement transactions from CSV text."""
    tenant = get_or_create_default_tenant(db)
    csv_text = payload.get("csv_text")
    if not csv_text:
        raise HTTPException(status_code=400, detail="csv_text is required")

    parsed = BankReconciliationService.parse_statement_csv(csv_text)
    if not parsed:
        raise HTTPException(status_code=400, detail="Could not parse any valid transaction rows from the CSV text.")

    created = BankReconciliationService.import_transactions(
        db, tenant.id, parsed, batch_name=payload.get("batch_name")
    )
    return {
        "status": "ok",
        "imported_count": len(created),
        "message": f"Imported {len(created)} bank transactions successfully."
    }


@app.get("/api/reconciliation/bank/transactions")
def list_bank_transactions(status: Optional[str] = None, db: Session = Depends(get_db)):
    """Lists imported bank transactions with optional filter (UNMATCHED, MATCHED)."""
    tenant = get_or_create_default_tenant(db)
    query = db.query(BankTransaction).filter(BankTransaction.tenant_id == tenant.id)
    if status and status.upper() != "ALL":
        query = query.filter(BankTransaction.status == status.upper())
    txns = query.order_by(BankTransaction.transaction_date.desc()).all()
    return [
        {
            "id": t.id,
            "statement_batch": t.statement_batch,
            "transaction_date": t.transaction_date.isoformat(),
            "description": t.description,
            "reference_no": t.reference_no,
            "withdrawal_amount": float(t.withdrawal_amount),
            "deposit_amount": float(t.deposit_amount),
            "balance_after": float(t.balance_after) if t.balance_after is not None else None,
            "status": t.status,
            "matched_invoice_id": t.matched_invoice_id,
            "reconciled_at": t.reconciled_at.isoformat() if t.reconciled_at else None,
            "reconciled_by": t.reconciled_by
        }
        for t in txns
    ]


@app.post("/api/reconciliation/bank/auto-match")
def auto_match_bank_transactions(db: Session = Depends(get_db)):
    """Executes deterministic rule-based matching between bank feed and ledger invoices."""
    tenant = get_or_create_default_tenant(db)
    result = BankReconciliationService.auto_reconcile(db, tenant.id)
    return {"status": "ok", "result": result}


@app.get("/api/reconciliation/bank/brs-report")
def get_bank_reconciliation_report(as_of_date: Optional[str] = None, db: Session = Depends(get_db)):
    """Generates official Bank Reconciliation Statement (BRS) reconciling General Ledger to Bank Statement."""
    tenant = get_or_create_default_tenant(db)
    target_date = date.fromisoformat(as_of_date) if as_of_date else date.today()
    return BankReconciliationService.generate_brs_statement(db, tenant.id, as_of_date=target_date)


# ==============================================================================
# GST RECONCILIATION & IMS (INVOICE MANAGEMENT SYSTEM) (P0 FIRM WORKSPACE)
# ==============================================================================

@app.post("/api/reconciliation/gst/upload-2b")
def upload_gstr2b_data(payload: dict, db: Session = Depends(get_db)):
    """Imports GSTR-2B static records for a return period (e.g. '102026')."""
    tenant = get_or_create_default_tenant(db)
    period = payload.get("return_period")
    records = payload.get("records", [])
    if not period or not records:
        raise HTTPException(status_code=400, detail="return_period and records list are required")

    created = GstReconciliationService.import_gstr2b_payload(
        db, tenant.id, return_period=period, records=records
    )
    return {
        "status": "ok",
        "return_period": period,
        "imported_records": len(created),
        "message": f"Imported {len(created)} GSTR-2B records for return period {period}."
    }


@app.get("/api/reconciliation/gst/summary")
def get_gst_reconciliation_summary(return_period: str = "102026", db: Session = Depends(get_db)):
    """Runs cross-reconciliation between Purchase Register and GSTR-2B, returning executive compliance metrics."""
    tenant = get_or_create_default_tenant(db)
    return GstReconciliationService.run_reconciliation(db, tenant.id, return_period=return_period)


@app.get("/api/reconciliation/gst/comparison")
def get_gstr2b_records(return_period: str = "102026", db: Session = Depends(get_db)):
    """Returns detailed line-by-line comparison grid of GSTR-2B entries and IMS actions."""
    tenant = get_or_create_default_tenant(db)
    entries = db.query(Gstr2bEntry).filter(
        Gstr2bEntry.tenant_id == tenant.id,
        Gstr2bEntry.return_period == return_period
    ).all()
    return [
        {
            "id": e.id,
            "return_period": e.return_period,
            "supplier_gstin": e.supplier_gstin,
            "supplier_name": e.supplier_name,
            "invoice_number": e.invoice_number,
            "invoice_date": e.invoice_date.isoformat(),
            "invoice_value": float(e.invoice_value),
            "taxable_value": float(e.taxable_value),
            "igst_amount": float(e.igst_amount),
            "cgst_amount": float(e.cgst_amount),
            "sgst_amount": float(e.sgst_amount),
            "itc_availability": e.itc_availability,
            "itc_blocked_reason": e.itc_blocked_reason,
            "ims_action": e.ims_action,
            "ims_action_at": e.ims_action_at.isoformat() if e.ims_action_at else None,
            "ims_action_by": e.ims_action_by,
            "reconciliation_status": e.reconciliation_status,
            "matched_invoice_id": e.matched_invoice_id
        }
        for e in entries
    ]


@app.post("/api/reconciliation/gst/ims-action")
def update_ims_action(payload: dict, db: Session = Depends(get_db)):
    """
    Submits an IMS (Invoice Management System) action for a GSTR-2B record:
    Allowed: ACCEPTED, REJECTED, PENDING, NO_ACTION.
    """
    tenant = get_or_create_default_tenant(db)
    entry_id = payload.get("entry_id")
    action = payload.get("action")
    checker = payload.get("performed_by", "MAKER_CHECKER_REVIEWER")
    if not entry_id or not action:
        raise HTTPException(status_code=400, detail="entry_id and action are required")

    try:
        updated = GstReconciliationService.set_ims_action(
            db, tenant.id, entry_id=entry_id, action=action, performed_by=checker
        )
        return {
            "status": "ok",
            "entry_id": updated.id,
            "ims_action": updated.ims_action,
            "message": f"IMS action updated to {updated.ims_action} successfully."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

