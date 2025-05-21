"""Jinja2 filter functions for the application."""

from datetime import datetime, date
from jinja2 import Undefined


def format_currency(amount, currency: str = "$") -> str:
    """Format a number as currency for templates.

    Handles ``None`` and Jinja2 ``Undefined`` values gracefully so that
    templates do not raise formatting errors when data is missing.
    """
    if amount is None or isinstance(amount, Undefined):
        return f"{currency}0.00"
    try:
        return f"{currency}{float(amount):,.2f}"
    except (TypeError, ValueError):
        return str(amount)


def format_date(value, fmt: str = "%b %d, %Y") -> str:
    """Safely format a date or datetime object for display."""
    if value is None or isinstance(value, Undefined):
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime(fmt)
    return str(value)

