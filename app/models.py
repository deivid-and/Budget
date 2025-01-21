import sqlite3
import os
import pytz
from datetime import datetime, timedelta
from .wise_api import fetch_transactions

# Database path and configuration
DB_DIR = os.path.join(os.path.dirname(__file__), 'database')
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DB_PATH = os.path.join(DB_DIR, 'database.db')
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "EUR")
TIMEZONE = os.getenv("TIMEZONE", "UTC")
USER_TIMEZONE = pytz.timezone(TIMEZONE)

def init_db():
    """
    Initializes the database and creates necessary tables.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

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
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS excluded_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL
        )
        """)
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
    Creates a budget with the specified amount and period (daily, weekly, monthly).
    """
    current_datetime = datetime.now(USER_TIMEZONE)

    if period == "daily":
        start_date = current_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = current_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
        name = "Daily Budget"
    elif period == "weekly":
        start_date = current_datetime - timedelta(days=current_datetime.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
        name = "Weekly Budget"
    elif period == "monthly":
        start_date = current_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (start_date + timedelta(days=32)).replace(day=1)
        end_date = next_month - timedelta(seconds=1)
        name = "Monthly Budget"
    else:
        raise ValueError("Invalid period. Choose 'daily', 'weekly', or 'monthly'.")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id FROM budgets
        WHERE name = ? AND start_date = ? AND end_date = ?
        """, (name, start_date.isoformat(), end_date.isoformat()))
        if cursor.fetchone():
            raise ValueError(f"A {name.lower()} already exists for this period.")
        
        cursor.execute("""
        INSERT INTO budgets (name, budget, start_date, end_date, spent)
        VALUES (?, ?, ?, ?, ?)
        """, (name, round(amount, 2), start_date.isoformat(), end_date.isoformat(), 0))
        conn.commit()

def delete_budget(budget_id):
    """
    Deletes a budget by its ID.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
        conn.commit()

def get_all_budgets():
    """
    Retrieves all budgets.
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
                "start_date": datetime.fromisoformat(row[3]).strftime("%Y-%m-%d %H:%M:%S"),
                "end_date": datetime.fromisoformat(row[4]).strftime("%Y-%m-%d %H:%M:%S"),
                "spent": round(row[5], 2),
            }
            for row in results
        ]

def add_manual_transaction(amount, date, description, time=None):
    """
    Adds a manual transaction to the database with proper date handling.
    """
    # Parse date if it's a string; ensure time is included
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")  # Parse as a date (no time)

    if time:
        # Combine date and time
        time_obj = datetime.strptime(time, "%H:%M").time()
        date = datetime.combine(date, time_obj)
    else:
        # Default to midnight if no time is provided
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Ensure date is now a proper datetime object
    if not isinstance(date, datetime):
        raise ValueError("Invalid date format. Expected a valid date.")

    # Insert the manual transaction
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO manual_transactions (amount, date, description)
        VALUES (?, ?, ?)
        """, (round(amount, 2), date.isoformat(), description))
        conn.commit()

def get_manual_transactions():
    """
    Retrieves manual transactions, including their IDs.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, amount, date, description
        FROM manual_transactions
        """)
        results = cursor.fetchall()

        transactions = []
        for row in results:
            try:
                date_str = row[2]
                if not isinstance(date_str, str):
                    raise ValueError("Invalid date format.")
                date = datetime.fromisoformat(date_str)
            except (TypeError, ValueError):
                date = datetime.now()

            transactions.append({
                "id": row[0],
                "amount": row[1],   
                "date": date.strftime("%Y-%m-%d %H:%M"),        
                "title": row[3], 
                "currency": DEFAULT_CURRENCY,
            })
        return transactions
    
def delete_manual_transaction(transaction_id):
    """
    Deletes a manual transaction from the database using its ID.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM manual_transactions WHERE id = ?", (transaction_id,))
        conn.commit()

def calculate_all_spent():
    """
    Calculates and updates spending for all budgets.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id, start_date, end_date FROM budgets")
        budgets = cursor.fetchall()

        cursor.execute("SELECT transaction_id FROM excluded_transactions")
        excluded_ids = {row[0] for row in cursor.fetchall()}
        transactions = fetch_transactions()

        for budget_id, start_date, end_date in budgets:
            start_date = datetime.fromisoformat(start_date).astimezone(USER_TIMEZONE)
            end_date = datetime.fromisoformat(end_date).astimezone(USER_TIMEZONE)
            total_spent = 0

            for transaction in transactions:
                try:
                    amount, currency = transaction["amount"].split()
                    if currency != DEFAULT_CURRENCY:
                        continue
                    transaction_date = datetime.strptime(transaction["date"], "%Y-%m-%d %H:%M:%S").astimezone(USER_TIMEZONE)
                    if transaction["id"] not in excluded_ids and start_date <= transaction_date <= end_date:
                        total_spent += float(amount.replace(",", ""))
                except (ValueError, KeyError):
                    continue

            manual_transactions = get_manual_transactions()
            for t in manual_transactions:
                transaction_date = datetime.strptime(t["date"], "%Y-%m-%d %H:%M").astimezone(USER_TIMEZONE)
                if start_date <= transaction_date <= end_date:
                    total_spent += t["amount"]

            cursor.execute("UPDATE budgets SET spent = ? WHERE id = ?", (round(total_spent, 2), budget_id))
        conn.commit()
