import os, re, requests, html, pytz
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

WISE_API_KEY = os.getenv("WISE_API_KEY")
WISE_PROFILE_ID = os.getenv("WISE_PROFILE_ID")
WISE_API_BASE_URL = os.getenv("WISE_API_BASE_URL")
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY")
TIMEZONE = os.getenv("TIMEZONE")
USER_TIMEZONE = pytz.timezone(TIMEZONE)

def clean_html_tags(text):
    """
    Removes HTML tags from the input text.
    """
    return re.sub(r'<.*?>', '', text)

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
    Fetches the transaction history from Wise in the default timezone.
    """
    try:
        url = f"{WISE_API_BASE_URL}/v1/profiles/{WISE_PROFILE_ID}/activities"
        headers = {"Authorization": f"Bearer {WISE_API_KEY}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        activities = response.json().get("activities", [])
        transactions = []

        for activity in activities:
            try:
                # Convert createdOn from UTC to the default timezone
                utc_time = datetime.fromisoformat(activity["createdOn"].replace("Z", "+00:00"))
                local_time = utc_time.astimezone(USER_TIMEZONE)

                transactions.append({
                    "id": activity["id"],
                    "amount": activity["primaryAmount"],
                    "title": clean_html_tags(activity.get("title", "No Title").strip()),
                    "date": local_time.strftime("%Y-%m-%d %H:%M:%S"),
                })
            except KeyError as e:
                print(f"Skipping malformed activity: {activity}. Missing key: {e}")
                continue

        return transactions
    except requests.RequestException as e:
        print(f"Error fetching transactions: {e}")
        return []