import sqlite3
import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from .models import (
    get_all_budgets,
    calculate_all_spent,
    add_manual_transaction,
    get_manual_transactions,
    create_budget,
    delete_budget,
)
from .wise_api import fetch_balance, fetch_transactions

# Database path and default currency
DB_PATH = "database/app.db"
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "MXN")

# Define the main Blueprint
main = Blueprint("main", __name__)

# Budget Routes
@main.route("/", methods=["GET"])
def index():
    """
    Main route for the app.
    Displays all budgets and calculates spending.
    """
    budgets = get_all_budgets()  # Fetch all budgets

    if not budgets:
        # No budgets exist; render a message in the template
        return render_template(
            "index.html",
            budgets=None,
            balance=fetch_balance(),
            transactions=fetch_transactions()[:10],
            manual_transactions=get_manual_transactions(),
            excluded_ids=excluded_ids,
            current_budget=None,
            DEFAULT_CURRENCY=DEFAULT_CURRENCY,
            error="No budgets exist. Please create a budget."
        )

    # Calculate spending for all budgets
    calculate_all_spent()
    balance = fetch_balance()
    transactions = fetch_transactions()[:10]  # Fetch recent transactions
    manual_transactions = get_manual_transactions()

        # Fetch excluded transactions
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT transaction_id FROM excluded_transactions
        """)
        excluded_ids = {row[0] for row in cursor.fetchall()}

    return render_template(
        "index.html",
        budgets=budgets,
        balance=balance,
        transactions=transactions,
        manual_transactions=manual_transactions,
        excluded_ids=excluded_ids,
        current_budget=budgets[0],
        DEFAULT_CURRENCY=DEFAULT_CURRENCY,
    )

@main.route("/budgets/create", methods=["POST"])
def create_budget_route():
    """
    Creates a new budget based on the submitted form data.
    """
    try:
        # Retrieve and validate form data
        amount = float(request.form.get("budget_amount"))
        if amount <= 0:
            raise ValueError("Budget amount must be greater than zero.")

        period = request.form.get("budget_period", "weekly").lower()
        if period not in ["daily", "weekly", "monthly"]:
            raise ValueError("Invalid budget period selected.")

        # Create the budget
        create_budget(amount, period)
        return redirect(url_for("main.index"))

    except ValueError as e:
        # Handle invalid inputs and display an error message
        return render_template(
            "index.html",
            error=str(e),
            budgets=get_all_budgets(),
            balance=fetch_balance(),
            transactions=fetch_transactions()[:10],
            manual_transactions=get_manual_transactions(),
            current_budget=None,
            DEFAULT_CURRENCY=DEFAULT_CURRENCY,
        )

@main.route("/budgets/delete/<int:budget_id>", methods=["POST"])
def delete_budget_route(budget_id):
    """
    Deletes a budget by its ID.
    """
    delete_budget(budget_id)
    return redirect(url_for("main.index"))

# Manual Transactions Routes
@main.route("/transactions/manual", methods=["POST"])
def add_manual_transaction_route():
    """
    Adds a manual transaction to the database.
    """
    try:
        title = request.form.get("title", "").strip()
        amount = float(request.form.get("amount"))
        date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
        if not title or amount <= 0:
            raise ValueError("Invalid transaction details.")

        add_manual_transaction(title, amount, date)
        return redirect(url_for("main.index"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@main.route("/transactions/manual", methods=["GET"])
def get_manual_transactions_route():
    """
    Retrieves manual transactions from the database.
    """
    transactions = get_manual_transactions()
    return jsonify(transactions)

# Exclude and Include Transactions Routes
@main.route("/transactions/exclude/<transaction_id>", methods=["POST"])
def exclude_transaction(transaction_id):
    """
    Excludes a transaction from budget calculations.
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
        print(f"Transaction {transaction_id} is already excluded.")
    except Exception as e:
        print(f"Error excluding transaction: {e}")

    return redirect(url_for("main.index"))

@main.route("/transactions/include/<transaction_id>", methods=["POST"])
def include_transaction(transaction_id):
    """
    Includes a previously excluded transaction in budget calculations.
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
        print(f"Error including transaction: {e}")

    return redirect(url_for("main.index"))
