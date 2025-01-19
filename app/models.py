import sqlite3
import os
import pytz
from datetime import datetime, timedelta
from .wise_api import fetch_transactions

# Database path and configuration
DB_PATH = "database/app.db"
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "EUR")
TIMEZONE = os.getenv("TIMEZONE", "UTC")
USER_TIMEZONE = pytz.timezone(TIMEZONE)

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

        # Create table for manual transactions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS manual_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL
        )
        """)

        conn.commit()


def create_budget(amount, period):
    """
    Creates a new budget with a specific amount and period (daily, weekly, monthly).
    Automatically calculates the start and end dates based on the period.
    """
    # Determine the current date in the user's timezone
    current_date = datetime.now(USER_TIMEZONE).date()

    # Calculate the start and end dates based on the budget period
    if period == "daily":
        start_date = current_date
        end_date = current_date
        name = "Daily Budget"
    elif period == "weekly":
        start_date = current_date - timedelta(days=current_date.weekday())  # Start of the week (Monday)
        end_date = start_date + timedelta(days=6)
        name = "Weekly Budget"
    elif period == "monthly":
        start_date = current_date.replace(day=1)  # First day of the current month
        next_month = (start_date + timedelta(days=32)).replace(day=1)  # First day of the next month
        end_date = next_month - timedelta(days=1)  # Last day of the current month
        name = "Monthly Budget"
    else:
        raise ValueError("Invalid period specified. Choose 'daily', 'weekly', or 'monthly'.")

    print(f"Creating {name}: {start_date} to {end_date}, Amount: {amount}")  # Debugging log

    # Insert the new budget into the database
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Check if a budget for the same period already exists
        cursor.execute("""
        SELECT id FROM budgets
        WHERE name = ? AND start_date = ? AND end_date = ?
        """, (name, start_date.isoformat(), end_date.isoformat()))
        
        if cursor.fetchone() is not None:
            raise ValueError(f"A {name.lower()} already exists for this period.")

        # Insert the new budget
        cursor.execute("""
        INSERT INTO budgets (name, budget, start_date, end_date, spent)
        VALUES (?, ?, ?, ?, ?)
        """, (name, round(amount, 2), start_date.isoformat(), end_date.isoformat(), 0))
        conn.commit()


def delete_budget(budget_id):
    """
    Deletes a budget from the database by its ID.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Delete the budget by ID
        cursor.execute("""
        DELETE FROM budgets
        WHERE id = ?
        """, (budget_id,))
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


def add_manual_transaction(amount, date, description):
    """
    Adds a manual transaction to the database.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO manual_transactions (amount, date, description)
        VALUES (?, ?, ?)
        """, (round(amount, 2), date.isoformat(), description))
        conn.commit()


def get_manual_transactions():
    """
    Retrieves all manual transactions from the database.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT amount, date, description
        FROM manual_transactions
        """)
        results = cursor.fetchall()
        return [
            {
                "amount": row[0],
                "date": datetime.fromisoformat(row[1]),
                "description": row[2],
            }
            for row in results
        ]


def calculate_all_spent():
    """
    Calculates and updates spending for all budgets, including manual and API transactions.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Fetch all budgets
        cursor.execute("""
        SELECT id, start_date, end_date
        FROM budgets
        """)
        budgets = cursor.fetchall()

        if not budgets:
            print("No budgets found.")
            return

        # Fetch excluded transactions
        cursor.execute("""
        SELECT transaction_id
        FROM excluded_transactions
        """)
        excluded_ids = {row[0] for row in cursor.fetchall()}

        # Fetch API transactions
        transactions = fetch_transactions()

        for budget in budgets:
            budget_id, start_date, end_date = budget
            start_date = datetime.fromisoformat(start_date)
            end_date = datetime.fromisoformat(end_date)

            total_spent = 0

            # Calculate API transactions for this budget
            for transaction in transactions:
                try:
                    amount, currency = transaction["amount"].split()
                    if currency != DEFAULT_CURRENCY:
                        continue
                    amount = round(float(amount.replace(",", "")), 2)
                    transaction_date = datetime.strptime(transaction["date"], "%Y-%m-%d %H:%M:%S")
                    transaction_id = transaction["id"]

                    if transaction_id in excluded_ids:
                        continue

                    if start_date <= transaction_date <= end_date:
                        total_spent += amount
                except (ValueError, KeyError):
                    continue

            # Calculate manual transactions for this budget
            manual_transactions = get_manual_transactions()
            for transaction in manual_transactions:
                if start_date <= transaction["date"] <= end_date:
                    total_spent += transaction["amount"]

            # Update the spent column for the current budget
            cursor.execute("""
            UPDATE budgets
            SET spent = ?
            WHERE id = ?
            """, (round(total_spent, 2), budget_id))
            print(f"Updated Budget {budget_id}: Spent = {round(total_spent, 2)}")

        conn.commit()
