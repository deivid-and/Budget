import sqlite3
import os
from datetime import datetime, timedelta
from .wise_api import fetch_transactions

# Database path
DB_PATH = "database/app.db"
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "MXN")


def init_db():
    """
    Initializes the SQLite database and creates necessary tables.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Create table for budgets
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            budget REAL NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            spent REAL DEFAULT 0
        )
        """)

        # Create table for excluded transactions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS excluded_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL
        )
        """)
        conn.commit()


def set_budget(name, amount, period):
    """
    Sets a new budget with a name, amount, and period (weekly, monthly).
    Clears the previous budget and inserts a new one.
    """
    start_date = datetime.now().date()

    if period == "weekly":
        end_date = start_date + timedelta(days=6)
    elif period == "monthly":
        end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    else:
        raise ValueError("Invalid budget period selected.")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Clear previous budgets
        cursor.execute("DELETE FROM budgets")
        # Insert the new budget
        cursor.execute("""
        INSERT INTO budgets (name, budget, start_date, end_date, spent)
        VALUES (?, ?, ?, ?, ?)
        """, (name, round(amount, 2), start_date, end_date, 0))
        conn.commit()


def get_all_budgets():
    """
    Retrieves all budgets from the database.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, name, budget, start_date, end_date, spent
        FROM budgets
        """)
        results = cursor.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "budget": round(row[2], 2),
                "start_date": row[3],
                "end_date": row[4],
                "spent": round(row[5], 2),
            }
            for row in results
        ]


def calculate_spent():
    """
    Calculates the total spending for the current budget period, excluding marked transactions.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Get the current budget period
        cursor.execute("SELECT start_date, end_date FROM budgets LIMIT 1")
        result = cursor.fetchone()

        if not result:
            print("No budget found.")
            return 0  # No budget set

        start_date, end_date = result
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)

        # Fetch excluded transactions
        cursor.execute("SELECT transaction_id FROM excluded_transactions")
        excluded_ids = {row[0] for row in cursor.fetchall()}

        # Fetch transactions and calculate spending
        transactions = fetch_transactions()
        total_spent = 0
        for transaction in transactions:
            try:
                amount, currency = transaction["amount"].split()
                amount = round(float(amount.replace(",", "")), 2)
                transaction_date = datetime.fromisoformat(transaction["date"].replace("Z", ""))
                transaction_id = transaction.get("id")

                # Skip excluded transactions
                if transaction_id in excluded_ids:
                    continue

                # Check if the transaction matches the budget period and currency
                if currency == DEFAULT_CURRENCY and start_date <= transaction_date <= end_date:
                    total_spent += amount
            except (ValueError, KeyError):
                continue

        # Update the spent column in the database
        total_spent = round(total_spent, 2)
        cursor.execute("""
        UPDATE budgets
        SET spent = ?
        WHERE start_date = ?
        """, (total_spent, start_date.date()))
        conn.commit()

        return total_spent
