from datetime import date


def calculate_tenure(hire_date: date | None, current_year: int) -> int | None:
    """Replicate the tenure calculation from the template."""
    if hire_date is None:
        return None
    tenure = current_year - hire_date.year
    if tenure < 0:
        tenure = 0
    return tenure


def test_future_hire_date_returns_zero():
    assert calculate_tenure(date(2025, 5, 15), 2024) == 0


def test_past_hire_date_returns_year_difference():
    assert calculate_tenure(date(2020, 6, 1), 2024) == 4
