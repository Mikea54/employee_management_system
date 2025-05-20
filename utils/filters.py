"""Jinja2 filter functions for the application."""

from datetime import datetime, date


def format_currency(amount, currency: str = "$"):
    """Format a number as currency for templates."""
    if amount is None:
        return f"{currency}0.00"
    return f"{currency}{amount:,.2f}"


def format_date(value, fmt: str = "%b %d, %Y"):
    """Safely format a date or datetime object for display."""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime(fmt)
    return str(value)
