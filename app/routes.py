import sqlite3
import os
from flask import Blueprint, render_template, request, redirect, url_for
from .models import create_default_budgets, get_all_budgets, calculate_spent
from .wise_api import fetch_balance, fetch_transactions

# Database path and default currency
DB_PATH = "database/app.db"
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "MXN")  # Default currency from environment variables

# Define the main Blueprint
main = Blueprint("main", __name__)

@main.route("/", methods=["GET", "POST"])
def index():
    """
    Main route for the app.
    Displays budgets, balance, and transactions.
    Handles form submission to set a new budget.
    """
    if request.method == "POST":
        try:

            # Validate and retrieve budget amount
            amount = float(request.form.get("budget_amount"))
            if amount <= 0:
                raise ValueError("Budget amount must be greater than zero.")

            # Validate and retrieve budget period
            period = request.form.get("budget_period", "weekly").lower()
            if period not in ["daily", "weekly", "monthly"]:
                raise ValueError("Invalid budget period selected.")

            # Create the budget in the database
            create_default_budgets()  # Ensure default budgets exist
            return redirect(url_for("main.index"))
        except ValueError as e:
            # Render the page with an error message on invalid input
            return render_template(
                "index.html",
                error=str(e),
                balance=None,
                transactions=None,
                budgets=None,
                DEFAULT_CURRENCY=DEFAULT_CURRENCY,
            )

    # Retrieve all budgets and calculate spent for the current budget
    create_default_budgets()  # Ensure default budgets are created
    budgets = get_all_budgets()  # Retrieve all budgets from the database
    current_budget = budgets[0] if budgets else None  # Use the first active budget
    if current_budget:
        current_budget["spent"] = calculate_spent()

    # Fetch balance and recent transactions
    try:
        balance = fetch_balance()
        transactions = fetch_transactions()[:5]  # Limit to the last 5 transactions
    except Exception as e:
        # Log and handle API errors gracefully
        print(f"Error fetching data: {e}")
        balance = None
        transactions = None

    # Render the index page with all required data
    return render_template(
        "index.html",
        budgets=budgets,
        balance=balance,
        transactions=transactions,
        current_budget=current_budget,
        DEFAULT_CURRENCY=DEFAULT_CURRENCY,
    )

@main.route("/exclude/<transaction_id>", methods=["POST"])
def exclude_transaction(transaction_id):
    """
    Exclude a transaction from budget calculations.
    Adds the transaction ID to the excluded_transactions table.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO excluded_transactions (transaction_id)
            VALUES (?)
            """, (transaction_id,))
            conn.commit()
    except sqlite3.IntegrityError:
        # Log if the transaction is already excluded
        print(f"Transaction {transaction_id} is already excluded.")
    except Exception as e:
        # Log unexpected errors
        print(f"Error excluding transaction {transaction_id}: {e}")

    # Recalculate spending after excluding the transaction
    calculate_spent()
    return redirect(url_for("main.index"))

@main.route("/include/<transaction_id>", methods=["POST"])
def include_transaction(transaction_id):
    """
    Include a previously excluded transaction in budget calculations.
    Removes the transaction ID from the excluded_transactions table.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            DELETE FROM excluded_transactions
            WHERE transaction_id = ?
            """, (transaction_id,))
            conn.commit()
    except Exception as e:
        # Log unexpected errors
        print(f"Error including transaction {transaction_id}: {e}")

    # Recalculate spending after including the transaction
    calculate_spent()
    return redirect(url_for("main.index"))
