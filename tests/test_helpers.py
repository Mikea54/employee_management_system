import datetime
from utils.helpers import calculate_leave_days, format_date, get_years_of_service


def test_calculate_leave_days_exclude_weekends():
    start = datetime.date(2024, 1, 1)  # Monday
    end = datetime.date(2024, 1, 7)    # Sunday
    assert calculate_leave_days(start, end, include_weekends=False) == 5


def test_calculate_leave_days_include_weekends():
    start = datetime.date(2024, 1, 1)  # Monday
    end = datetime.date(2024, 1, 7)    # Sunday
    assert calculate_leave_days(start, end, include_weekends=True) == 7


def test_calculate_leave_days_invalid_range():
    start = datetime.date(2024, 1, 7)
    end = datetime.date(2024, 1, 1)
    assert calculate_leave_days(start, end) == 0


def test_format_date_with_datetime():
    dt = datetime.datetime(2024, 1, 1, 12, 34, 56)
    assert format_date(dt) == "2024-01-01 12:34:56"


def test_format_date_with_date():
    d = datetime.date(2024, 1, 1)
    assert format_date(d) == "2024-01-01"


def test_get_years_of_service_exactly_one_year():
    today = datetime.date.today()
    hire_date = today - datetime.timedelta(days=365)
    assert get_years_of_service(hire_date) == 1


def test_get_years_of_service_anniversary_not_reached():
    today = datetime.date.today()
    one_year_ago = today - datetime.timedelta(days=365)
    hire_date = one_year_ago + datetime.timedelta(days=30)
    assert get_years_of_service(hire_date) == 0


def test_get_years_of_service_none():
    assert get_years_of_service(None) == 0
