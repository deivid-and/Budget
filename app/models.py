import sqlite3
from datetime import datetime, timedelta
from .wise_api import fetch_transactions  # Ensure this is imported for transaction fetching

# Database path
DB_PATH = "database/app.db"

def init_db():
    """
    Initializes the SQLite database and creates necessary tables.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Create table for weekly budget
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weekly_budget REAL NOT NULL,
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

def set_weekly_budget(amount):
    """
    Sets the weekly budget by clearing any existing record and inserting a new one.
    """
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=6)  # Weekly budget ends in 7 days
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Clear the previous budget
        cursor.execute("DELETE FROM weekly_budget")
        # Insert the new budget
        cursor.execute("""
        INSERT INTO weekly_budget (weekly_budget, start_date, end_date, spent)
        VALUES (?, ?, ?, ?)
        """, (round(amount, 2), start_date, end_date, 0))
        conn.commit()

def get_weekly_budget():
    """
    Retrieves the current weekly budget data from the database.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT weekly_budget, start_date, end_date, spent
        FROM weekly_budget
        LIMIT 1
        """)
        result = cursor.fetchone()
        if result:
            return {
                "weekly_budget": round(result[0], 2),
                "start_date": result[1],
                "end_date": result[2],
                "spent": round(result[3], 2),
            }
        return None

def calculate_weekly_spent():
    """
    Calculates the total spending for the current week, excluding marked transactions.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Get the current budget period
        cursor.execute("SELECT start_date, end_date FROM weekly_budget LIMIT 1")
        result = cursor.fetchone()

        if not result:
            print("No weekly budget found.")
            return 0  # No budget set

        start_date, end_date = result
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)

        # Fetch excluded transactions
        cursor.execute("SELECT transaction_id FROM excluded_transactions")
        excluded_ids = {row[0] for row in cursor.fetchall()}
        print(f"Excluded transactions: {excluded_ids}")  # Debugging output

        # Fetch transactions and calculate spending
        transactions = fetch_transactions()
        print(f"Fetched transactions: {transactions}")  # Debugging output
        total_spent = 0
        for transaction in transactions:
            try:
                # Extract transaction details
                amount, currency = transaction["amount"].split()
                amount = round(float(amount.replace(",", "")), 2)  # Remove commas and round to 2 decimals
                transaction_date = datetime.fromisoformat(transaction["date"].replace("Z", ""))
                transaction_id = transaction.get("id")  # Extract transaction ID

                # Skip excluded transactions
                if transaction_id in excluded_ids:
                    print(f"Skipping excluded transaction: {transaction_id}")
                    continue

                # Check if the transaction is within the current week and in MXN
                if currency == "MXN" and start_date <= transaction_date <= end_date:
                    total_spent += amount
                    print(f"Included transaction: {transaction}")  # Debugging output
            except (ValueError, KeyError) as e:
                print(f"Skipping transaction due to error: {e}")  # Debugging output
                continue

        # Round the total spent and update the 'spent' column in the database
        total_spent = round(total_spent, 2)
        cursor.execute("""
        UPDATE weekly_budget
        SET spent = ?
        WHERE start_date = ? AND end_date = ?
        """, (total_spent, start_date.date(), end_date.date()))
        conn.commit()

        print(f"Total spent updated: {total_spent}")  # Debugging output
        return total_spent
