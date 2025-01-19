from datetime import datetime

def format_date(date):
    """
    Formats a date object into MM/DD/YY format.
    """
    return date.strftime("%m/%d/%y") if isinstance(date, datetime) else None

def format_time(date):
    """
    Formats a date object into HH:MM AM/PM format.
    """
    return date.strftime("%I:%M %p") if isinstance(date, datetime) else None

def format_datetime(date):
    """
    Formats a date object into MM/DD/YY HH:MM AM/PM format.
    """
    return date.strftime("%m/%d/%y %I:%M %p") if isinstance(date, datetime) else None
