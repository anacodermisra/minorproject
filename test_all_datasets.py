"""Comprehensive Test Suite for Real-World (IRL) and Synthetic Invoices.

Evaluates every file in:
- data/test_datasets/computer_generated_invoices/
- data/test_datasets/real_world_invoices/

Checks:
1. Ingestion & table layout extraction
2. Field extraction (Invoice #, Vendor, Dates, Totals, Lines)
3. Arithmetic & Tax Invariants
4. Accounting Interpretation & Balanced Double-Entry verification (Debits == Credits)
5. Ground-Truth verification (where paired JSON exists)
"""

import glob
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

# Ensure backend is on PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "backend"))

# Ensure utf-8 stdout encoding on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.engine.ingestion import DocumentIngestionService
from app.engine.invariants import run_comprehensive_validation
from app.engine.interpreter import AccountingInterpreter
from app.schemas.accounting import ValidationCheckStatus


def money(val):
    if val is None:
        return Decimal("0.00")
    return Decimal(str(val)).quantize(Decimal("0.01"))


def test_invoice(pdf_path: str, json_path: str = None) -> dict:
    filename = os.path.basename(pdf_path)
    result = {
        "file": filename,
        "success": False,
        "errors": [],
        "warnings": [],
        "extracted": {},
        "invariants": {},
        "accounting": {},
        "gt_comparison": None,
    }

    # 1. Ingestion
    try:
        extracted = DocumentIngestionService.process_pdf_invoice(pdf_path)
    except Exception as exc:
        result["errors"].append(f"Ingestion failed: {exc}")
        return result

    result["extracted"] = {
        "invoice_number": extracted.invoice_number,
        "vendor_name": extracted.vendor_name,
        "invoice_date": str(extracted.invoice_date) if extracted.invoice_date else None,
        "subtotal": float(extracted.subtotal) if extracted.subtotal else 0.0,
        "total_tax": float(extracted.total_tax) if extracted.total_tax else 0.0,
        "total_discount": float(extracted.total_discount) if extracted.total_discount else 0.0,
        "grand_total": float(extracted.grand_total) if extracted.grand_total else 0.0,
        "line_items_count": len(extracted.line_items),
        "confidence": extracted.confidence.value if hasattr(extracted.confidence, "value") else str(extracted.confidence),
    }

    # 2. Accounting Interpretation
    try:
        proposal = AccountingInterpreter.interpret_invoice(
            invoice=extracted,
            document_id="test-doc-id",
            creditor_account_code="2010",
        )
        total_debits = sum(money(line.amount) for line in proposal.lines if line.entry_type.value == "DEBIT")
        total_credits = sum(money(line.amount) for line in proposal.lines if line.entry_type.value == "CREDIT")
        is_balanced = total_debits == total_credits

        result["accounting"] = {
            "transaction_type": proposal.transaction_type.value,
            "lines_count": len(proposal.lines),
            "total_debits": float(total_debits),
            "total_credits": float(total_credits),
            "is_balanced": is_balanced,
            "requires_human_review": proposal.requires_human_review,
        }
        if not is_balanced:
            result["errors"].append(f"Double-entry imbalance: Debits ({total_debits}) != Credits ({total_credits})")

    except Exception as exc:
        result["errors"].append(f"Accounting interpretation failed: {exc}")
        proposal = None

    # 3. Invariants Validation
    if proposal:
        from app.db.seed_accounts import STANDARD_CHART_OF_ACCOUNTS
        active_codes = {acc["code"] for acc in STANDARD_CHART_OF_ACCOUNTS}
        report = run_comprehensive_validation(
            invoice=extracted,
            entry=proposal,
            active_account_codes=active_codes,
            is_duplicate=False,
        )
        failed_checks = [c.check_name for c in report.checks if c.status == ValidationCheckStatus.FAIL]
        warning_checks = [c.check_name for c in report.checks if c.status == ValidationCheckStatus.WARNING]
        result["invariants"] = {
            "is_valid": report.is_valid,
            "can_post_automatically": report.can_post_automatically,
            "has_blocking_failures": report.has_blocking_failures,
            "failed_checks": failed_checks,
            "warning_checks": warning_checks,
        }
        if failed_checks:
            result["errors"].extend([f"Invariant Fail: {c}" for c in failed_checks])
        if warning_checks:
            result["warnings"].extend([f"Invariant Warning: {c}" for c in warning_checks])

    # 4. Ground-Truth Comparison
    if json_path and os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                gt = json.load(f)

            gt_checks = {}
            # Match grand total
            expected_total = gt.get("grand_total") or gt.get("totalAmount")
            if expected_total is not None:
                gt_checks["grand_total_matched"] = money(extracted.grand_total) == money(expected_total)
                gt_checks["expected_total"] = float(expected_total)
                gt_checks["actual_total"] = float(extracted.grand_total)

            # Match invoice number
            expected_inv_num = gt.get("invoice_number") or gt.get("documentNumber")
            if expected_inv_num:
                clean_exp = "".join(expected_inv_num.split()).casefold()
                clean_act = "".join(str(extracted.invoice_number or "").split()).casefold()
                gt_checks["invoice_num_matched"] = clean_exp in clean_act or clean_act in clean_exp
                gt_checks["expected_inv_num"] = expected_inv_num
                gt_checks["actual_inv_num"] = extracted.invoice_number

            result["gt_comparison"] = gt_checks
        except Exception as exc:
            result["warnings"].append(f"Ground-truth comparison error: {exc}")

    result["success"] = len(result["errors"]) == 0
    return result


def main():
    print("=" * 80)
    print("  AI ACCOUNTING SYSTEM - COMPREHENSIVE INVOICE EVALUATION TEST RUNNER")
    print("=" * 80)

    test_dirs = [
        ("Computer-Generated (Synthetic) Invoices", BASE_DIR / "data" / "test_datasets" / "computer_generated_invoices"),
        ("Real-World (IRL) Invoices & Benchmarks", BASE_DIR / "data" / "test_datasets" / "real_world_invoices"),
    ]

    summary_stats = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "balanced_journals": 0,
        "gt_matches": 0,
    }

    for suite_name, folder_path in test_dirs:
        print(f"\n>>> Running Suite: {suite_name}")
        print(f"    Location: {folder_path}\n")

        pdf_files = sorted(glob.glob(str(folder_path / "*.pdf")))
        if not pdf_files:
            print("    No PDF files found.")
            continue

        for pdf in pdf_files:
            summary_stats["total"] += 1
            stem = os.path.splitext(pdf)[0]
            json_file = f"{stem}.json" if os.path.exists(f"{stem}.json") else None

            res = test_invoice(pdf, json_file)
            status_tag = "[PASS]" if res["success"] else "[FLAG]"
            if res["success"]:
                summary_stats["passed"] += 1
            else:
                summary_stats["failed"] += 1

            if res["accounting"].get("is_balanced"):
                summary_stats["balanced_journals"] += 1

            print(f"{status_tag} {res['file']}")
            ext = res["extracted"]
            print(f"       Extracted: Inv #{ext.get('invoice_number')} | Vendor: {ext.get('vendor_name')} | Total: {ext.get('grand_total')} | Lines: {ext.get('line_items_count')} | Conf: {ext.get('confidence')}")

            if res["accounting"]:
                acc = res["accounting"]
                print(f"       Journal: Type={acc.get('transaction_type')} | Debits={acc.get('total_debits')} | Credits={acc.get('total_credits')} | Balanced={acc.get('is_balanced')}")

            if res["gt_comparison"]:
                gt = res["gt_comparison"]
                tot_match = gt.get("grand_total_matched")
                num_match = gt.get("invoice_num_matched")
                if tot_match:
                    summary_stats["gt_matches"] += 1
                print(f"       Ground Truth Match: Total Match={tot_match} (Exp: {gt.get('expected_total')}, Act: {gt.get('actual_total')}) | Inv# Match={num_match}")

            if res["warnings"]:
                print(f"       Warnings: {'; '.join(res['warnings'][:3])}")
            if res["errors"]:
                print(f"       Errors: {'; '.join(res['errors'])}")
            print()

    print("=" * 80)
    print("  TEST SUMMARY SCORECARD")
    print("=" * 80)
    print(f"Total Invoices Tested:          {summary_stats['total']}")
    print(f"Passed All Hard Invariants:     {summary_stats['passed']} / {summary_stats['total']}")
    print(f"Balanced Double-Entry Journals: {summary_stats['balanced_journals']} / {summary_stats['total']}")
    print(f"Ground Truth Exact Matches:     {summary_stats['gt_matches']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
