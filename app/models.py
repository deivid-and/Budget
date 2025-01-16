import sqlite3, os, pytz
from datetime import datetime, timedelta
from .wise_api import fetch_transactions

# Database path
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
        conn.commit()

def create_default_budgets():
    """
    Automatically creates daily, weekly, and monthly budgets if they do not already exist.
    """
    current_date = datetime.now(USER_TIMEZONE).date()

    # Define budget periods
    daily_start = current_date
    daily_end = current_date

    weekly_start = current_date - timedelta(days=current_date.weekday())  # Start of the week (Monday)
    weekly_end = weekly_start + timedelta(days=6)

    monthly_start = current_date.replace(day=1)  # Start of the month
    next_month = (monthly_start + timedelta(days=32)).replace(day=1)
    monthly_end = next_month - timedelta(days=1)  # Last day of the month

    budgets_to_create = [
        {"name": "Daily Budget", "start_date": daily_start, "end_date": daily_end, "budget": 0.0},
        {"name": "Weekly Budget", "start_date": weekly_start, "end_date": weekly_end, "budget": 0.0},
        {"name": "Monthly Budget", "start_date": monthly_start, "end_date": monthly_end, "budget": 0.0},
    ]


    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for budget in budgets_to_create:
            # Check if the budget already exists
            cursor.execute("""
            SELECT id FROM budgets
            WHERE name = ? AND start_date = ? AND end_date = ?
            """, (budget["name"], budget["start_date"].isoformat(), budget["end_date"].isoformat()))
            
            if cursor.fetchone() is None:  # If not exists, create it
                cursor.execute("""
                INSERT INTO budgets (name, budget, start_date, end_date, spent)
                VALUES (?, ?, ?, ?, ?)
                """, (budget["name"], 0.0, budget["start_date"].isoformat(), budget["end_date"].isoformat(), 0))
                print(f"Created Budget: {budget['name']} for {budget['start_date']} to {budget['end_date']}")  # Debugging
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

        print(f"Budget Period: {start_date} to {end_date}")  # Debugging

        # Fetch excluded transactions
        cursor.execute("SELECT transaction_id FROM excluded_transactions")
        excluded_ids = {row[0] for row in cursor.fetchall()}
        print(f"Excluded Transactions: {excluded_ids}")  # Debugging

        # Fetch transactions
        transactions = fetch_transactions()
        print(f"Fetched Transactions: {transactions}")  # Debugging

        total_spent = 0

        for transaction in transactions:
            try:
                # Parse transaction details
                amount, currency = transaction["amount"].split()
                if currency != DEFAULT_CURRENCY:
                    print(f"Skipping Transaction: {transaction} due to currency mismatch.")
                    continue
                amount = round(float(amount.replace(",", "")), 2)
                transaction_date = datetime.strptime(transaction["date"], "%Y-%m-%d %H:%M:%S")
                transaction_id = transaction["id"]

                # Debugging: Check transaction details
                print(f"Transaction: {transaction}")

                # Skip excluded transactions
                if transaction_id in excluded_ids:
                    print(f"Excluded Transaction: {transaction_id}")
                    continue

                # Include only transactions in the current currency and budget period
                if start_date <= transaction_date <= end_date:
                    total_spent += amount
                    print(f"Included Transaction: {transaction}")
            except (ValueError, KeyError) as e:
                print(f"Skipping Transaction: {transaction} due to error: {e}")
                continue

        # Update the spent column in the database
        total_spent = round(total_spent, 2)
        print(f"Total Spent Calculated: {total_spent}")  # Debugging
        cursor.execute("""
        UPDATE budgets
        SET spent = ?
        WHERE start_date = ?
        """, (total_spent, start_date.date()))
        conn.commit()

        return total_spent


