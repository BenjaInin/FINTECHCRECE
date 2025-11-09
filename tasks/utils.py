from .utils import format_date, format_money
# utils.py

def format_date(date):
    return date.strftime('%d-%b-%Y') if date else ''

def format_money(amount):
    return f"${amount:,.2f}"
