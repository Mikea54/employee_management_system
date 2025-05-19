"""Jinja2 filter functions for the application."""

def format_currency(amount, currency='$'):
    """Format a number as currency"""
    if amount is None:
        return f"{currency}0.00"
    return f"{currency}{amount:,.2f}"