import sqlite3
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.db.session import engine, SessionLocal
from app.db.seed_accounts import seed_standard_accounts
from app.models.accounting import Tenant, Account

def migrate():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "accounting_system.db"))
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    def add_col_if_missing(table, col, col_type):
        cur.execute(f"PRAGMA table_info({table});")
        cols = [r[1] for r in cur.fetchall()]
        if col not in cols:
            print(f"Adding column '{col}' to table '{table}'...")
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")

    add_col_if_missing("tenants", "business_type", "TEXT DEFAULT 'IT_SERVICES'")
    add_col_if_missing("invoices", "invoice_type", "TEXT DEFAULT 'PURCHASE'")
    add_col_if_missing("invoices", "payment_status", "TEXT DEFAULT 'UNPAID'")
    add_col_if_missing("invoices", "amount_paid", "NUMERIC DEFAULT 0.00")
    add_col_if_missing("invoices", "financial_year", "TEXT")
    add_col_if_missing("journal_entries", "invoice_id", "TEXT")
    add_col_if_missing("journal_entries", "financial_year", "TEXT")
    add_col_if_missing("journal_entries", "payment_reference", "TEXT")

    con.commit()
    con.close()
    print("Database columns verified and migrated successfully.")

    # Seed accounts
    db = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        for t in tenants:
            seed_standard_accounts(db, t.id)
            print(f"Accounts synced for tenant: {t.name}")
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
