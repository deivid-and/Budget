import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

WISE_API_KEY = os.getenv("WISE_API_KEY")
WISE_PROFILE_ID = os.getenv("WISE_PROFILE_ID")
WISE_API_BASE_URL = os.getenv("WISE_API_BASE_URL")
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY")

# Validate that required environment variables are set
if not WISE_API_KEY or not WISE_PROFILE_ID or not WISE_API_BASE_URL:
    raise ValueError("Missing required environment variables: WISE_API_KEY, WISE_PROFILE_ID, or WISE_API_BASE_URL.")

def fetch_balance():
    """
    Fetches the balance from Wise.
    Returns the balance as a float or None if not found.
    """
    try:
        url = f"{WISE_API_BASE_URL}/v4/profiles/{WISE_PROFILE_ID}/balances?types=STANDARD"
        headers = {"Authorization": f"Bearer {WISE_API_KEY}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Parse response
        balances = response.json()
        for balance in balances:
            if balance["currency"] == DEFAULT_CURRENCY:
                return float(balance["amount"]["value"])
        print(f"{DEFAULT_CURRENCY} balance not found.")
        return None
    except requests.RequestException as e:
        print(f"Error fetching balance: {e}")
        return None

def fetch_transactions():
    """
    Fetches the transaction history from Wise.
    Returns a list of transactions or an empty list if no transactions are found.
    """
    try:
        url = f"{WISE_API_BASE_URL}/v1/profiles/{WISE_PROFILE_ID}/activities"
        headers = {"Authorization": f"Bearer {WISE_API_KEY}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Parse response
        activities = response.json().get("activities", [])
        transactions = []
        for activity in activities:
            try:
                # Format each transaction and ensure necessary fields exist
                transactions.append({
                    "id": activity["id"],  # Include the transaction ID for exclusion functionality
                    "amount": activity["primaryAmount"],
                    "title": activity.get("title", "No Title").strip(),
                    "date": activity["createdOn"]
                })
            except KeyError as e:
                print(f"Skipping malformed activity: {activity}. Missing key: {e}")
                continue

        return transactions
    except requests.RequestException as e:
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
