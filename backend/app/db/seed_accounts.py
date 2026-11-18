from sqlalchemy.orm import Session
from app.models.accounting import Tenant, Account
from app.schemas.accounting import AccountCategory, NormalBalance


STANDARD_CHART_OF_ACCOUNTS = [
    # ASSETS (1000 - 1999)
    {"code": "1010", "name": "Cash in Hand", "category": AccountCategory.ASSET, "normal_balance": NormalBalance.DEBIT, "description": "Liquid cash balances"},
    {"code": "1020", "name": "Current Bank Account", "category": AccountCategory.ASSET, "normal_balance": NormalBalance.DEBIT, "description": "Operating bank account"},
    {"code": "1030", "name": "Accounts Receivable / Debtors", "category": AccountCategory.ASSET, "normal_balance": NormalBalance.DEBIT, "description": "Customer trade receivables from credit sales"},
    {"code": "1040", "name": "Merchandise Inventory / Stock in Hand", "category": AccountCategory.ASSET, "normal_balance": NormalBalance.DEBIT, "description": "Trading goods inventory held for resale"},
    {"code": "1050", "name": "Office Furniture & Fixtures", "category": AccountCategory.ASSET, "normal_balance": NormalBalance.DEBIT, "description": "Capitalized furniture & fixtures meeting capitalization policy"},
    {"code": "1060", "name": "IT & Computer Equipment", "category": AccountCategory.ASSET, "normal_balance": NormalBalance.DEBIT, "description": "Capitalized computers, servers, and high-value IT equipment"},
    {"code": "1070", "name": "Office Equipment & Machinery", "category": AccountCategory.ASSET, "normal_balance": NormalBalance.DEBIT, "description": "Capitalized office machinery and equipment"},
    {"code": "1081", "name": "Input CGST A/c", "category": AccountCategory.ASSET, "normal_balance": NormalBalance.DEBIT, "description": "Eligible Input Central GST credit receivable"},
    {"code": "1082", "name": "Input SGST A/c", "category": AccountCategory.ASSET, "normal_balance": NormalBalance.DEBIT, "description": "Eligible Input State GST credit receivable"},
    {"code": "1083", "name": "Input IGST A/c", "category": AccountCategory.ASSET, "normal_balance": NormalBalance.DEBIT, "description": "Eligible Input Integrated GST credit receivable"},
    {"code": "1084", "name": "Ineligible / Blocked Input Tax Credit", "category": AccountCategory.ASSET, "normal_balance": NormalBalance.DEBIT, "description": "Taxes held pending eligibility verification or capital adjustment"},

    # LIABILITIES (2000 - 2999)
    {"code": "2010", "name": "Accounts Payable / Creditors", "category": AccountCategory.LIABILITY, "normal_balance": NormalBalance.CREDIT, "description": "Trade creditors and supplier payables"},
    {"code": "2081", "name": "Output CGST A/c", "category": AccountCategory.LIABILITY, "normal_balance": NormalBalance.CREDIT, "description": "Central GST collected on sales payable to government"},
    {"code": "2082", "name": "Output SGST A/c", "category": AccountCategory.LIABILITY, "normal_balance": NormalBalance.CREDIT, "description": "State GST collected on sales payable to government"},
    {"code": "2083", "name": "Output IGST A/c", "category": AccountCategory.LIABILITY, "normal_balance": NormalBalance.CREDIT, "description": "Integrated GST collected on inter-state sales payable to government"},

    # EQUITY (3000 - 3999)
    {"code": "3010", "name": "Owner Capital", "category": AccountCategory.EQUITY, "normal_balance": NormalBalance.CREDIT, "description": "Equity investment and contributed capital"},

    # REVENUE (4000 - 4999)
    {"code": "4010", "name": "Sales & Service Revenue", "category": AccountCategory.REVENUE, "normal_balance": NormalBalance.CREDIT, "description": "Operating income from sales and services"},

    # EXPENSES (5000 - 5999)
    {"code": "5005", "name": "Purchases of Trading Goods / COGS", "category": AccountCategory.EXPENSE, "normal_balance": NormalBalance.DEBIT, "description": "Cost of trading goods purchased for resale by retail or commercial businesses"},
    {"code": "5010", "name": "Office Supplies & Stationery", "category": AccountCategory.EXPENSE, "normal_balance": NormalBalance.DEBIT, "description": "Paper, pens, toner, consumable office stationery"},
    {"code": "5020", "name": "Server, Cloud & Software Expense", "category": AccountCategory.EXPENSE, "normal_balance": NormalBalance.DEBIT, "description": "Cloud hosting, SaaS subscriptions, software licenses"},
    {"code": "5030", "name": "Office Rent Expense", "category": AccountCategory.EXPENSE, "normal_balance": NormalBalance.DEBIT, "description": "Office premises rental and lease costs"},
    {"code": "5040", "name": "Electricity & Utility Expense", "category": AccountCategory.EXPENSE, "normal_balance": NormalBalance.DEBIT, "description": "Power, water, heating, and general utilities"},
    {"code": "5050", "name": "Freight, Shipping & Cartage Expense", "category": AccountCategory.EXPENSE, "normal_balance": NormalBalance.DEBIT, "description": "Delivery, courier, handling and transport charges for revenue items"},
    {"code": "5060", "name": "Computer Accessories & Peripherals Expense", "category": AccountCategory.EXPENSE, "normal_balance": NormalBalance.DEBIT, "description": "Cables, adapters, docking stations, keyboards under capitalization threshold"},
    {"code": "5070", "name": "Repairs, Maintenance & Services Expense", "category": AccountCategory.EXPENSE, "normal_balance": NormalBalance.DEBIT, "description": "Equipment servicing, repairs, and general upkeep"},
    {"code": "5080", "name": "Ineligible Input GST Expense", "category": AccountCategory.EXPENSE, "normal_balance": NormalBalance.DEBIT, "description": "Non-recoverable GST expensed as part of purchase cost under Section 17(5)"},
]


def seed_standard_accounts(db: Session, tenant_id: str) -> int:
    """
    Populates standard Chart of Accounts for a newly created or existing tenant.
    Idempotent: Only creates accounts that do not already exist for this tenant.
    Does not duplicate accounts or overwrite existing user modifications.
    """
    existing_accounts = db.query(Account).filter(Account.tenant_id == tenant_id).all()
    existing_codes = {acc.code for acc in existing_accounts}

    accounts_to_create = []
    for acc_data in STANDARD_CHART_OF_ACCOUNTS:
        if acc_data["code"] not in existing_codes:
            account = Account(
                tenant_id=tenant_id,
                code=acc_data["code"],
                name=acc_data["name"],
                category=acc_data["category"],
                normal_balance=acc_data["normal_balance"],
                description=acc_data.get("description"),
                is_active=True
            )
            accounts_to_create.append(account)

    if accounts_to_create:
        db.add_all(accounts_to_create)
        db.commit()

    return len(accounts_to_create)
