import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for
from .models import set_weekly_budget, get_weekly_budget, calculate_weekly_spent
from .wise_api import fetch_balance, fetch_transactions

# Database path (used in exclude_transaction)
DB_PATH = "database/app.db"

main = Blueprint("main", __name__)

@main.route("/", methods=["GET", "POST"])
def index():
    """
    Main route to display budget, balance, and transactions.
    Handles form submission to set the weekly budget.
    """
    # Handle form submission to set the weekly budget
    if request.method == "POST":
        try:
            # Parse and set the weekly budget
            amount = float(request.form.get("weekly_budget"))
            set_weekly_budget(amount)
            return redirect(url_for("main.index"))
        except ValueError:
            # Handle invalid input and display an error message
            return render_template(
                "index.html",
                error="Invalid budget amount. Please enter a valid number.",
                balance=None,
                transactions=None,
                budget_data=None,
            )

    # Fetch budget data and calculate weekly spending
    budget_data = get_weekly_budget()
    if budget_data:
        budget_data["spent"] = calculate_weekly_spent()

    # Fetch Wise balance and transactions
    try:
        balance = fetch_balance()
        transactions = fetch_transactions()[:5]  # Limit to the last 5 transactions
    except Exception as e:
        # Handle errors during API calls gracefully
        print(f"Error fetching data: {e}")
        balance = None
        transactions = None

    # Render the template with fetched data
    return render_template(
        "index.html",
        balance=balance,
        transactions=transactions,
        budget_data=budget_data,
    )

@main.route("/exclude/<transaction_id>", methods=["POST"])
def exclude_transaction(transaction_id):
    """
    Marks a transaction as excluded from the weekly budget calculation.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Add transaction ID to the excluded_transactions table
            cursor.execute("""
            INSERT INTO excluded_transactions (transaction_id)
            VALUES (?)
            """, (transaction_id,))
            conn.commit()
    except sqlite3.IntegrityError:
        # Handle cases where the transaction is already excluded
        print(f"Transaction {transaction_id} is already excluded.")
    except Exception as e:
        # Handle any unexpected errors
        print(f"Error excluding transaction {transaction_id}: {e}")

    # Recalculate spending after excluding the transaction
    calculate_weekly_spent()
    return redirect(url_for("main.index"))
