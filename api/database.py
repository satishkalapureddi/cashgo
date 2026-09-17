import sqlite3
from datetime import datetime

DATABASE_NAME = "cashgo.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            transaction_id TEXT UNIQUE NOT NULL,

            cash_amount_paise INTEGER NOT NULL,
            service_charge_paise INTEGER NOT NULL,
            total_amount_paise INTEGER NOT NULL,

            currency TEXT NOT NULL DEFAULT 'INR',

            status TEXT NOT NULL DEFAULT 'payment_pending',

            payment_provider TEXT,
            provider_payment_id TEXT,
            qr_id TEXT,

            expires_at TEXT NOT NULL,

            cash_dispensed INTEGER NOT NULL DEFAULT 0,

            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def create_transaction(
    transaction_id,
    cash_amount_paise,
    service_charge_paise,
    total_amount_paise,
    expires_at,
    payment_provider="demo",
    qr_id=None
):
    connection = get_connection()

    connection.execute("""
        INSERT INTO transactions (
            transaction_id,
            cash_amount_paise,
            service_charge_paise,
            total_amount_paise,
            currency,
            status,
            payment_provider,
            qr_id,
            expires_at,
            cash_dispensed,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        transaction_id,
        cash_amount_paise,
        service_charge_paise,
        total_amount_paise,
        "INR",
        "payment_pending",
        payment_provider,
        qr_id,
        expires_at,
        0,
        datetime.now().isoformat()
    ))

    connection.commit()
    connection.close()


def get_transaction(transaction_id):
    connection = get_connection()

    transaction = connection.execute("""
        SELECT *
        FROM transactions
        WHERE transaction_id = ?
    """, (transaction_id,)).fetchone()

    connection.close()

    return transaction



def update_payment_status(transaction_id, status):
    connection = get_connection()

    connection.execute("""
        UPDATE transactions
        SET status = ?
        WHERE transaction_id = ?
    """, (
        status,
        transaction_id
    ))

    connection.commit()
    connection.close()


def dispense_cash(transaction_id):
    connection = get_connection()

    transaction = connection.execute("""
        SELECT *
        FROM transactions
        WHERE transaction_id = ?
    """, (transaction_id,)).fetchone()

    if transaction is None:
        connection.close()
        return {
            "success": False,
            "message": "Transaction not found"
        }

    if transaction["status"] != "payment_verified":
        connection.close()
        return {
            "success": False,
            "message": "Payment is not verified"
        }

    if transaction["cash_dispensed"]:
        connection.close()
        return {
            "success": False,
            "message": "Cash already dispensed"
        }

    connection.execute("""
        UPDATE transactions
        SET status = ?,
            cash_dispensed = 1
        WHERE transaction_id = ?
          AND status = ?
          AND cash_dispensed = 0
    """, (
        "cash_dispensed",
        transaction_id,
        "payment_verified"
    ))

    connection.commit()

    updated = connection.execute("""
        SELECT *
        FROM transactions
        WHERE transaction_id = ?
    """, (transaction_id,)).fetchone()

    connection.close()

    return {
        "success": True,
        "transaction_id": updated["transaction_id"],
        "cash_amount": updated["cash_amount_paise"] // 100,
        "payment_status": updated["status"],
        "cash_status": "dispensed"
    }    