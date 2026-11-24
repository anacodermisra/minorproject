import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.accounting import (
    Tenant,
    Invoice,
    Gstr2bEntry,
    AuditLog,
)


class GstReconciliationService:
    """
    Indian GST GSTR-2B and IMS (Invoice Management System) Reconciliation Service.
    
    Functions:
    1. Import GSTR-2B records (from JSON or structured payload).
    2. Cross-reconcile against the internal Purchase Register (posted purchase invoices).
    3. Categorize line statuses: MATCHED, IN_BOOKS_ONLY, IN_GSTR2B_ONLY, VALUE_MISMATCH.
    4. Manage statutory IMS actions (ACCEPT, REJECT, PENDING) as mandated by GSTN.
    5. Screen Section 17(5) blocked Input Tax Credits.
    """

    @classmethod
    def import_gstr2b_payload(
        cls,
        db: Session,
        tenant_id: str,
        return_period: str,
        records: List[Dict]
    ) -> List[Gstr2bEntry]:
        """Imports GSTR-2B records for a given return period (e.g. '102026' or '2026-10')."""
        created = []
        for r in records:
            inv_date = r["invoice_date"]
            if isinstance(inv_date, str):
                inv_date = date.fromisoformat(inv_date)

            entry = Gstr2bEntry(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                return_period=return_period,
                supplier_gstin=r["supplier_gstin"].strip().upper(),
                supplier_name=r.get("supplier_name", "Supplier").strip(),
                invoice_number=r["invoice_number"].strip(),
                invoice_type=r.get("invoice_type", "B2B"),
                invoice_date=inv_date,
                invoice_value=Decimal(str(r.get("invoice_value", 0))),
                taxable_value=Decimal(str(r.get("taxable_value", 0))),
                igst_amount=Decimal(str(r.get("igst_amount", 0))),
                cgst_amount=Decimal(str(r.get("cgst_amount", 0))),
                sgst_amount=Decimal(str(r.get("sgst_amount", 0))),
                itc_availability=r.get("itc_availability", "Y").upper(),
                itc_blocked_reason=r.get("itc_blocked_reason"),
                ims_action="NO_ACTION",
                reconciliation_status="GSTR2B_ONLY"
            )
            db.add(entry)
            created.append(entry)
        db.commit()
        return created

    @classmethod
    def run_reconciliation(cls, db: Session, tenant_id: str, return_period: str) -> Dict:
        """
        Reconciles GSTR-2B against Purchase Invoices for the given period.
        """
        gstr2b_records = db.query(Gstr2bEntry).filter(
            Gstr2bEntry.tenant_id == tenant_id,
            Gstr2bEntry.return_period == return_period
        ).all()

        purchase_invoices = db.query(Invoice).filter(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "PURCHASE"
        ).all()

        matched_count = 0
        value_mismatch_count = 0
        in_2b_only_count = 0

        # Map purchase invoices by (clean_inv_no, gstin)
        inv_map = {}
        for inv in purchase_invoices:
            k = (inv.invoice_number.strip().lower(), (inv.vendor_gstin or "").strip().upper())
            inv_map[k] = inv

        matched_inv_ids = set()

        for g in gstr2b_records:
            k = (g.invoice_number.strip().lower(), g.supplier_gstin)
            matched_inv = inv_map.get(k)

            # Fallback match by invoice number only if unique
            if not matched_inv:
                candidates = [inv for inv in purchase_invoices if inv.invoice_number.strip().lower() == g.invoice_number.strip().lower()]
                if len(candidates) == 1:
                    matched_inv = candidates[0]

            if matched_inv:
                matched_inv_ids.add(matched_inv.id)
                g.matched_invoice_id = matched_inv.id
                # Compare totals (₹1 tolerance for rounding differences)
                tot_diff = abs(g.invoice_value - matched_inv.grand_total)
                if tot_diff <= Decimal("1.00"):
                    g.reconciliation_status = "MATCHED"
                    # Default IMS action to ACCEPT if ITC is available
                    if g.ims_action == "NO_ACTION" and g.itc_availability == "Y":
                        g.ims_action = "ACCEPTED"
                    matched_count += 1
                else:
                    g.reconciliation_status = "VALUE_MISMATCH"
                    value_mismatch_count += 1
            else:
                g.reconciliation_status = "GSTR2B_ONLY"
                in_2b_only_count += 1

        db.commit()

        # Invoices in books but not in 2B
        in_books_only = [inv for inv in purchase_invoices if inv.id not in matched_inv_ids]

        # Calculate totals
        total_2b_itc = sum((g.igst_amount + g.cgst_amount + g.sgst_amount for g in gstr2b_records if g.itc_availability == "Y"), start=Decimal("0.00"))
        accepted_itc = sum((g.igst_amount + g.cgst_amount + g.sgst_amount for g in gstr2b_records if g.ims_action == "ACCEPTED"), start=Decimal("0.00"))
        blocked_itc = sum((g.igst_amount + g.cgst_amount + g.sgst_amount for g in gstr2b_records if g.itc_availability == "N"), start=Decimal("0.00"))

        return {
            "return_period": return_period,
            "total_gstr2b_records": len(gstr2b_records),
            "matched_records": matched_count,
            "value_mismatch_records": value_mismatch_count,
            "in_gstr2b_only": in_2b_only_count,
            "in_books_only": len(in_books_only),
            "total_2b_available_itc": float(total_2b_itc),
            "ims_accepted_itc": float(accepted_itc),
            "blocked_sec_17_5_itc": float(blocked_itc)
        }

    @classmethod
    def set_ims_action(
        cls,
        db: Session,
        tenant_id: str,
        entry_id: str,
        action: str,
        performed_by: str = "AUDIT_CHECKER"
    ) -> Gstr2bEntry:
        """
        Updates the IMS (Invoice Management System) action for a GSTR-2B record:
        Valid actions: ACCEPTED, REJECTED, PENDING, NO_ACTION.
        """
        valid_actions = {"ACCEPTED", "REJECTED", "PENDING", "NO_ACTION"}
        action_upper = action.strip().upper()
        if action_upper not in valid_actions:
            raise ValueError(f"Invalid IMS action: '{action}'. Must be one of {valid_actions}")

        entry = db.query(Gstr2bEntry).filter(
            Gstr2bEntry.id == entry_id,
            Gstr2bEntry.tenant_id == tenant_id
        ).first()

        if not entry:
            raise ValueError(f"GSTR-2B record not found with id: {entry_id}")

        old_action = entry.ims_action
        entry.ims_action = action_upper
        entry.ims_action_at = datetime.now(timezone.utc)
        entry.ims_action_by = performed_by

        # Audit log
        audit = AuditLog(
            tenant_id=tenant_id,
            entity_name="Gstr2bEntry",
            entity_id=entry.id,
            action="IMS_ACTION",
            performed_by=performed_by,
            user_role="CHECKER",
            details=f"IMS action for Inv #{entry.invoice_number} ({entry.supplier_gstin}) changed from {old_action} to {action_upper}."
        )
        db.add(audit)
        db.commit()
        db.refresh(entry)
        return entry
