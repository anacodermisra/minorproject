from decimal import Decimal
from datetime import date
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.accounting import (
    Tenant,
    Account,
    JournalEntry,
    JournalLine,
    EntryPostingStatus,
)
from app.schemas.accounting import AccountCategory, NormalBalance, EntryType
from app.engine.ledger import generate_trial_balance


class FinancialStatementService:
    """
    Generates verified Profit & Loss Statements, Balance Sheets, and Monthly Analytics
    directly from authoritative double-entry journal postings.
    """

    @classmethod
    def generate_profit_and_loss(
        cls,
        db: Session,
        tenant_id: str,
        as_of_date: Optional[date] = None,
        financial_year: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates Net Profit / Loss = Total Revenue - Total Expenses
        optionally filtered by as_of_date and financial_year.
        """
        if as_of_date is None:
            as_of_date = date.today()

        tb = generate_trial_balance(db, tenant_id, as_of_date=as_of_date, financial_year=financial_year)

        revenue_items = []
        expense_items = []
        total_revenue = Decimal("0.00")
        total_expenses = Decimal("0.00")

        for row in tb.rows:
            if row.category == "REVENUE":
                revenue_items.append({"code": row.account_code, "name": row.account_name, "amount": row.closing_balance})
                total_revenue += row.closing_balance
            elif row.category == "EXPENSE":
                expense_items.append({"code": row.account_code, "name": row.account_name, "amount": row.closing_balance})
                total_expenses += row.closing_balance

        net_profit = (total_revenue - total_expenses).quantize(Decimal("0.01"))

        return {
            "as_of_date": as_of_date.isoformat(),
            "financial_year": financial_year,
            "revenues": revenue_items,
            "total_revenue": total_revenue,
            "expenses": expense_items,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "is_profitable": net_profit >= Decimal("0.00")
        }

    @classmethod
    def generate_balance_sheet(
        cls,
        db: Session,
        tenant_id: str,
        as_of_date: Optional[date] = None,
        financial_year: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates Assets = Liabilities + Equity + Net Profit as of a given date.
        """
        if as_of_date is None:
            as_of_date = date.today()

        tb = generate_trial_balance(db, tenant_id, as_of_date=as_of_date, financial_year=financial_year)
        pnl = cls.generate_profit_and_loss(db, tenant_id, as_of_date=as_of_date, financial_year=financial_year)
        net_profit = pnl["net_profit"]

        assets = []
        liabilities = []
        equity = []

        total_assets = Decimal("0.00")
        total_liabilities = Decimal("0.00")
        total_equity = Decimal("0.00")

        for row in tb.rows:
            if row.category == "ASSET":
                assets.append({"code": row.account_code, "name": row.account_name, "amount": row.closing_balance})
                total_assets += row.closing_balance
            elif row.category == "LIABILITY":
                liabilities.append({"code": row.account_code, "name": row.account_name, "amount": row.closing_balance})
                total_liabilities += row.closing_balance
            elif row.category == "EQUITY":
                equity.append({"code": row.account_code, "name": row.account_name, "amount": row.closing_balance})
                total_equity += row.closing_balance

        # Add Net Profit to Equity section
        retained_earnings = net_profit
        total_equity_with_earnings = (total_equity + retained_earnings).quantize(Decimal("0.01"))
        total_liabilities_and_equity = (total_liabilities + total_equity_with_earnings).quantize(Decimal("0.01"))

        is_balanced = total_assets == total_liabilities_and_equity

        return {
            "as_of_date": as_of_date.isoformat(),
            "financial_year": financial_year,
            "assets": assets,
            "total_assets": total_assets,
            "liabilities": liabilities,
            "total_liabilities": total_liabilities,
            "equity": equity,
            "retained_earnings": retained_earnings,
            "total_equity": total_equity_with_earnings,
            "total_liabilities_and_equity": total_liabilities_and_equity,
            "is_balanced": is_balanced
        }

    @classmethod
    def generate_monthly_analytics(
        cls,
        db: Session,
        tenant_id: str,
        financial_year: str = "FY 2026-27"
    ) -> List[Dict[str, Any]]:
        """
        Produces month-by-month financial metrics across an Indian Financial Year (Apr to Mar):
        Revenue, Expenses, Input Tax Credit (ITC), Output Tax Collected, and Net Cash Flow.
        """
        import calendar

        # Parse start and end years from "FY 2026-27"
        try:
            parts = financial_year.replace("FY", "").strip().split("-")
            start_yr = int(parts[0])
            end_yr = 2000 + int(parts[1]) if len(parts[1]) == 2 else int(parts[1])
        except Exception:
            start_yr = 2026
            end_yr = 2027

        months_config = [
            (4, start_yr, "Apr"), (5, start_yr, "May"), (6, start_yr, "Jun"),
            (7, start_yr, "Jul"), (8, start_yr, "Aug"), (9, start_yr, "Sep"),
            (10, start_yr, "Oct"), (11, start_yr, "Nov"), (12, start_yr, "Dec"),
            (1, end_yr, "Jan"), (2, end_yr, "Feb"), (3, end_yr, "Mar")
        ]

        results = []

        for m_num, yr, m_name in months_config:
            # Query journal lines posted in this exact month and year
            last_day = calendar.monthrange(yr, m_num)[1]
            start_d = date(yr, m_num, 1)
            end_d = date(yr, m_num, last_day)

            lines = (
                db.query(JournalLine)
                .join(JournalEntry)
                .join(Account)
                .filter(
                    JournalEntry.tenant_id == tenant_id,
                    JournalEntry.status == EntryPostingStatus.POSTED,
                    JournalEntry.entry_date >= start_d,
                    JournalEntry.entry_date <= end_d
                )
                .all()
            )

            rev = Decimal("0.00")
            exp = Decimal("0.00")
            itc = Decimal("0.00")
            out_tax = Decimal("0.00")
            cash_in = Decimal("0.00")
            cash_out = Decimal("0.00")
            tx_count = len({l.entry_id for l in lines})

            for line in lines:
                acc_code = line.account.code
                cat = line.account.category
                amt = Decimal(str(line.amount))

                # Revenue (Credits to Revenue accounts)
                if cat == AccountCategory.REVENUE and line.entry_type == EntryType.CREDIT:
                    rev += amt
                # Expense (Debits to Expense accounts)
                elif cat == AccountCategory.EXPENSE and line.entry_type == EntryType.DEBIT:
                    exp += amt
                # Input Tax Credit (Debits to 1081, 1082, 1083)
                elif acc_code in ("1081", "1082", "1083") and line.entry_type == EntryType.DEBIT:
                    itc += amt
                # Output GST (Credits to 2081, 2082, 2083)
                elif acc_code in ("2081", "2082", "2083") and line.entry_type == EntryType.CREDIT:
                    out_tax += amt
                # Cash & Bank flows (1010 Cash, 1020 Bank)
                elif acc_code in ("1010", "1020"):
                    if line.entry_type == EntryType.DEBIT:
                        cash_in += amt
                    else:
                        cash_out += amt

            results.append({
                "month": f"{m_name} {yr}",
                "month_short": m_name,
                "year": yr,
                "month_number": m_num,
                "revenue": float(rev),
                "expenses": float(exp),
                "net_profit": float(rev - exp),
                "itc_claimed": float(itc),
                "output_tax": float(out_tax),
                "cash_inflow": float(cash_in),
                "cash_outflow": float(cash_out),
                "net_cash_flow": float(cash_in - cash_out),
                "transaction_count": tx_count
            })

        return results

    @classmethod
    def generate_trading_and_pnl(
        cls,
        db: Session,
        tenant_id: str,
        as_of_date: Optional[date] = None,
        financial_year: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Produces Indian statutory Trading Account (Gross Profit) and Profit & Loss Account (Net Profit).
        Trading: Sales - Cost of Goods Sold (Trading Purchases 5005) = Gross Profit
        P&L: Gross Profit + Other Income - Indirect Operating Overheads = Net Operating Profit
        """
        if as_of_date is None:
            as_of_date = date.today()

        tb = generate_trial_balance(db, tenant_id, as_of_date=as_of_date, financial_year=financial_year)

        sales_revenue = Decimal("0.00")
        cogs_purchases = Decimal("0.00")
        other_income = Decimal("0.00")
        indirect_expenses = []
        total_indirect_expenses = Decimal("0.00")

        for row in tb.rows:
            code = row.account_code
            closing = row.closing_balance

            if code == "4010":
                sales_revenue += closing
            elif code == "4020":
                other_income += closing
            elif code in ("5005", "1040"):  # Direct Trading Purchases / COGS
                cogs_purchases += closing
            elif row.category == "EXPENSE":
                indirect_expenses.append({
                    "code": code,
                    "name": row.account_name,
                    "amount": float(closing)
                })
                total_indirect_expenses += closing

        gross_profit = (sales_revenue - cogs_purchases).quantize(Decimal("0.01"))
        net_profit = (gross_profit + other_income - total_indirect_expenses).quantize(Decimal("0.01"))

        return {
            "as_of_date": as_of_date.isoformat(),
            "financial_year": financial_year,
            "trading_account": {
                "sales_revenue": float(sales_revenue),
                "cost_of_goods_sold": float(cogs_purchases),
                "gross_profit": float(gross_profit),
                "is_gross_profit": gross_profit >= Decimal("0.00")
            },
            "profit_and_loss_account": {
                "gross_profit_bf": float(gross_profit),
                "other_income": float(other_income),
                "indirect_expenses": indirect_expenses,
                "total_indirect_expenses": float(total_indirect_expenses),
                "net_profit": float(net_profit),
                "is_net_profit": net_profit >= Decimal("0.00")
            }
        }

    @classmethod
    def generate_account_ledger_folio(
        cls,
        db: Session,
        tenant_id: str,
        account_code: str,
        financial_year: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates individual T-account ledger folio for any Account Code,
        showing chronological debit and credit movements, opposite particulars, and running balance.
        """
        account = db.query(Account).filter(Account.tenant_id == tenant_id, Account.code == account_code).first()
        if not account:
            return {"error": f"Account with code {account_code} not found."}

        query = (
            db.query(JournalLine)
            .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
            .filter(
                JournalLine.account_id == account.id,
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.status == EntryPostingStatus.POSTED
            )
        )
        if financial_year:
            query = query.filter(JournalEntry.financial_year == financial_year)

        lines = query.order_by(JournalEntry.entry_date.asc(), JournalEntry.created_at.asc()).all()

        running_balance = Decimal("0.00")
        transactions = []

        is_normal_debit = account.normal_balance == NormalBalance.DEBIT

        for l in lines:
            amt = Decimal(str(l.amount))
            is_debit = l.entry_type == EntryType.DEBIT

            if is_normal_debit:
                running_balance += amt if is_debit else -amt
            else:
                running_balance += -amt if is_debit else amt

            transactions.append({
                "id": l.id,
                "entry_id": l.entry_id,
                "date": l.entry.entry_date.isoformat(),
                "invoice_number": l.entry.invoice_number,
                "particulars": l.description or l.entry.narration,
                "debit": float(amt) if is_debit else None,
                "credit": float(amt) if not is_debit else None,
                "running_balance": float(abs(running_balance)),
                "balance_type": "Dr" if running_balance >= 0 else "Cr"
            })

        return {
            "account_code": account.code,
            "account_name": account.name,
            "category": account.category.value,
            "normal_balance": account.normal_balance.value,
            "financial_year": financial_year,
            "total_transactions": len(transactions),
            "closing_balance": float(abs(running_balance)),
            "closing_balance_type": "Dr" if running_balance >= 0 else "Cr",
            "transactions": transactions
        }
