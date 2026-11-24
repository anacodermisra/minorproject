import os
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.accounting  # Ensure all models are registered in Base.metadata
from app.main import app
from app.db.session import Base, get_db

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_invoices"))


@pytest.fixture
def client():
    # Provide isolated database session for end-to-end API tests using StaticPool for in-memory SQLite
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_api_health_and_tenant(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res_t = client.get("/api/tenant")
    assert res_t.status_code == 200
    assert res_t.json()["name"] == "Modern Tech Solutions Pvt Ltd"


def test_api_list_accounts(client):
    res = client.get("/api/accounts")
    assert res.status_code == 200
    accounts = res.json()
    assert len(accounts) >= 10
    codes = [a["code"] for a in accounts]
    assert "1050" in codes  # Furniture
    assert "1081" in codes  # Input CGST
    assert "2010" in codes  # Creditors


def test_api_end_to_end_invoice_flow(client):
    """
    Simulates complete REST API flow:
    Upload PDF -> Process Document -> Verify Extracted Proposal -> Post Entry -> Check Trial Balance & Reports
    """
    pdf_path = os.path.join(DATA_DIR, "INV-2026-001.pdf")
    assert os.path.exists(pdf_path)

    # 1. Upload Document
    with open(pdf_path, "rb") as f:
        upload_res = client.post(
            "/api/documents/upload",
            files={"file": ("INV-2026-001.pdf", f, "application/pdf")}
        )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document_id"]
    assert doc_id is not None

    # 2. Process Document (Extraction + Table Correction + Interpretation)
    process_res = client.post(f"/api/documents/{doc_id}/process")
    assert process_res.status_code == 200
    data = process_res.json()
    
    inv = data["extracted_invoice"]
    proposal = data["proposed_journal_entry"]

    assert inv["invoice_number"] == "INV-2026-001"
    assert inv["grand_total"] == 59000.00
    assert proposal["total_debits"] == 59000.00
    assert proposal["total_credits"] == 59000.00
    assert proposal["is_balanced"] is True

    # 3. Post the proposed journal entry
    post_res = client.post("/api/journal/post", json=proposal)
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "SUCCESS"

    # 4. Check Trial Balance
    tb_res = client.get("/api/reports/trial-balance")
    assert tb_res.status_code == 200
    tb = tb_res.json()
    assert tb["is_balanced"] is True
    assert tb["total_debit_balance"] >= 59000.00
    assert tb["total_credit_balance"] >= 59000.00

    # 5. Check Balance Sheet (Asset = Desks 30,000 + Input GST 9,000 = 39,000; Chairs 20,000 expensed)
    bs_res = client.get("/api/reports/balance-sheet")
    assert bs_res.status_code == 200
    bs = bs_res.json()
    assert bs["is_balanced"] is True
    assert bs["total_assets"] >= 39000.00

    # 6. Check Audit Logs
    audit_res = client.get("/api/reports/audit-logs")
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) > 0
    assert any(l["action"] == "POST" for l in logs)


def test_duplicate_upload_blocked(client):
    """Verifies that uploading the exact same file twice is rejected via SHA-256 hash."""
    pdf_path = os.path.join(DATA_DIR, "INV-2026-001.pdf")
    with open(pdf_path, "rb") as f:
        res1 = client.post("/api/documents/upload", files={"file": ("INV-2026-001.pdf", f, "application/pdf")})
    assert res1.status_code == 200

    # Second upload of the exact same content
    with open(pdf_path, "rb") as f:
        res2 = client.post("/api/documents/upload", files={"file": ("INV-2026-001.pdf", f, "application/pdf")})
    assert res2.status_code == 400
    assert "Duplicate file detected" in res2.json()["detail"]


def test_statutory_immutability_and_contra_reversal(client):
    """
    Verifies that:
    1. A posted invoice document cannot be hard-deleted (statutory ledger immutability).
    2. A posted journal entry can be reversed via contra entry (/api/journal/reverse/{id}).
    3. The reversal creates balancing contra lines and preserves audit invariants.
    """
    pdf_path = os.path.join(DATA_DIR, "INV-2026-001.pdf")
    with open(pdf_path, "rb") as f:
        upload_res = client.post("/api/documents/upload", files={"file": ("INV-2026-001.pdf", f, "application/pdf")})
    doc_id = upload_res.json()["document_id"]

    # Process and Post
    process_res = client.post(f"/api/documents/{doc_id}/process")
    proposal = process_res.json()["proposed_journal_entry"]
    post_res = client.post("/api/journal/post", json=proposal)
    entry_id = post_res.json()["journal_entry_id"]

    # 1. Attempt to delete posted document -> Must fail with 400
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 400
    assert "Statutory ledger immutability" in del_res.json()["detail"]

    # 2. Execute contra reversal
    rev_res = client.post(f"/api/journal/reverse/{entry_id}", json={"reason": "Customer cancellation test"})
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["status"] == "SUCCESS"
    assert rev_data["reversal_entry_id"] is not None

    # 3. Check Trial Balance remains balanced after reversal
    tb_res = client.get("/api/reports/trial-balance")
    assert tb_res.status_code == 200
    assert tb_res.json()["is_balanced"] is True

    # 4. Attempting to reverse again must be rejected
    rev_again = client.post(f"/api/journal/reverse/{entry_id}", json={"reason": "Duplicate reversal test"})
    assert rev_again.status_code == 400
    assert "already been reversed" in rev_again.json()["detail"]


def test_posted_invoice_edit_prohibited(client):
    """
    Code Risk 2 Fix Verification:
    Verifies that once an invoice/voucher is posted to the general ledger,
    direct edits to line items, amounts, or parties via PUT /api/documents/{doc_id}/invoice
    are strictly rejected with HTTP 409 Conflict to protect the audit trail.
    """
    pdf_path = os.path.join(DATA_DIR, "INV-2026-001.pdf")
    with open(pdf_path, "rb") as f:
        upload_res = client.post("/api/documents/upload", files={"file": ("INV-2026-001.pdf", f, "application/pdf")})
    doc_id = upload_res.json()["document_id"]

    # Process and Post
    process_res = client.post(f"/api/documents/{doc_id}/process")
    proposal = process_res.json()["proposed_journal_entry"]
    post_res = client.post("/api/journal/post", json=proposal)
    assert post_res.status_code == 200

    # Attempt to edit posted invoice -> Must fail with 409 Conflict
    edit_res = client.put(
        f"/api/documents/{doc_id}/invoice",
        json={"vendor_name": "Tampered Furniture Vendor", "grand_total": 99999.00}
    )
    assert edit_res.status_code == 409
    assert "Statutory ledger immutability" in edit_res.json()["detail"]


def test_post_journal_tampering_rejected(client):
    """
    Code Risk 1 Fix Verification:
    Verifies that the server validates client-supplied journal proposals against
    the authoritative source invoice voucher. Tampered totals must be rejected with HTTP 400.
    """
    pdf_path = os.path.join(DATA_DIR, "INV-2026-001.pdf")
    with open(pdf_path, "rb") as f:
        upload_res = client.post("/api/documents/upload", files={"file": ("INV-2026-001.pdf", f, "application/pdf")})
    doc_id = upload_res.json()["document_id"]

    process_res = client.post(f"/api/documents/{doc_id}/process")
    proposal = process_res.json()["proposed_journal_entry"]

    # Client tampers with proposal line amounts before posting
    tampered_proposal = dict(proposal)
    tampered_proposal["lines"] = [dict(l) for l in proposal["lines"]]
    tampered_proposal["lines"][0]["amount"] = 999999.00
    tampered_proposal["lines"][-1]["amount"] = 999999.00

    post_res = client.post("/api/journal/post", json=tampered_proposal)
    assert post_res.status_code == 400
    assert "Voucher integrity violation" in post_res.json()["detail"]


def test_period_lock_enforcement(client):
    """
    P0 Accounting Firm Control:
    Verifies that locking a period (e.g. '2026-10') prevents direct voucher postings.
    """
    # 1. Lock period
    lock_res = client.post("/api/periods/lock", json={"period_key": "2026-10", "reason": "Statutory October close"})
    assert lock_res.status_code == 200
    assert lock_res.json()["is_locked"] is True

    # 2. Upload and process October invoice
    pdf_path = os.path.join(DATA_DIR, "INV-2026-001.pdf")
    with open(pdf_path, "rb") as f:
        upload_res = client.post("/api/documents/upload", files={"file": ("INV-2026-001.pdf", f, "application/pdf")})
    doc_id = upload_res.json()["document_id"]
    process_res = client.post(f"/api/documents/{doc_id}/process")
    proposal = process_res.json()["proposed_journal_entry"]

    # 3. Attempt posting into locked period -> Must fail with HTTP 423 Locked
    post_res = client.post("/api/journal/post", json=proposal)
    assert post_res.status_code == 423
    assert "Statutory Period Lock" in post_res.json()["detail"]

    # 4. Unlock period and post -> Must now succeed
    unlock_res = client.post("/api/periods/unlock", json={"period_key": "2026-10", "reason": "Auditor review"})
    assert unlock_res.status_code == 200
    assert unlock_res.json()["is_locked"] is False

    post_ok = client.post("/api/journal/post", json=proposal)
    assert post_ok.status_code == 200
    assert post_ok.json()["status"] == "SUCCESS"


def test_bank_reconciliation_cycle(client):
    """
    P0 Bank Feed Import and Reconciliation (BRS):
    Imports bank CSV, matches payments against invoices, and generates BRS report.
    """
    # 1. Post an invoice
    pdf_path = os.path.join(DATA_DIR, "INV-2026-001.pdf")
    with open(pdf_path, "rb") as f:
        upload_res = client.post("/api/documents/upload", files={"file": ("INV-2026-001.pdf", f, "application/pdf")})
    doc_id = upload_res.json()["document_id"]
    process_res = client.post(f"/api/documents/{doc_id}/process")
    client.post("/api/journal/post", json=process_res.json()["proposed_journal_entry"])

    # 2. Upload bank statement CSV with matching withdrawal
    csv_content = (
        "Date,Description,Ref No,Withdrawal,Deposit,Balance\n"
        "2026-10-20,NEFT Vendor Payment INV-2026-001 ABC Furniture,UTR123456,59000.00,0.00,441000.00\n"
        "2026-10-21,Bank Monthly Service Charges,CHG001,500.00,0.00,440500.00\n"
    )
    import_res = client.post("/api/reconciliation/bank/upload-csv", json={"csv_text": csv_content})
    assert import_res.status_code == 200
    assert import_res.json()["imported_count"] == 2

    # 3. Auto reconcile
    match_res = client.post("/api/reconciliation/bank/auto-match")
    assert match_res.status_code == 200
    res_data = match_res.json()["result"]
    assert res_data["newly_matched"] >= 1

    # 4. Check BRS Statement
    brs_res = client.get("/api/reconciliation/bank/brs-report?as_of_date=2026-10-31")
    assert brs_res.status_code == 200
    brs = brs_res.json()
    assert "bank_statement_balance" in brs
    assert "gl_book_balance" in brs


def test_gstr2b_reconciliation_and_ims_workflow(client):
    """
    P0 GST Reconciliation & IMS Workspace:
    Reconciles GSTR-2B against books and executes IMS actions (ACCEPTED / REJECTED).
    """
    # 1. Post invoice
    pdf_path = os.path.join(DATA_DIR, "INV-2026-001.pdf")
    with open(pdf_path, "rb") as f:
        upload_res = client.post("/api/documents/upload", files={"file": ("INV-2026-001.pdf", f, "application/pdf")})
    doc_id = upload_res.json()["document_id"]
    process_res = client.post(f"/api/documents/{doc_id}/process")
    client.post("/api/journal/post", json=process_res.json()["proposed_journal_entry"])

    # 2. Upload GSTR-2B static filing from supplier
    gstr2b_payload = {
        "return_period": "102026",
        "records": [
            {
                "supplier_gstin": "07AAAAA0000A1Z5",
                "supplier_name": "ABC Furniture Mart",
                "invoice_number": "INV-2026-001",
                "invoice_date": "2026-10-15",
                "invoice_value": 59000.00,
                "taxable_value": 50000.00,
                "igst_amount": 0.00,
                "cgst_amount": 4500.00,
                "sgst_amount": 4500.00,
                "itc_availability": "Y"
            }
        ]
    }
    upload_2b_res = client.post("/api/reconciliation/gst/upload-2b", json=gstr2b_payload)
    assert upload_2b_res.status_code == 200

    # 3. Run reconciliation summary
    summary_res = client.get("/api/reconciliation/gst/summary?return_period=102026")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["matched_records"] == 1
    assert summary["total_2b_available_itc"] == 9000.00

    # 4. View comparison grid
    grid_res = client.get("/api/reconciliation/gst/comparison?return_period=102026")
    assert grid_res.status_code == 200
    records = grid_res.json()
    assert len(records) == 1
    entry_id = records[0]["id"]
    assert records[0]["reconciliation_status"] == "MATCHED"

    # 5. Submit IMS action
    ims_res = client.post(
        "/api/reconciliation/gst/ims-action",
        json={"entry_id": entry_id, "action": "ACCEPTED", "performed_by": "TAX_REVIEWER"}
    )
    assert ims_res.status_code == 200
    assert ims_res.json()["ims_action"] == "ACCEPTED"


