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

