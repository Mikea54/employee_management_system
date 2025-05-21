from datetime import datetime, date
from types import SimpleNamespace

from routes import attendance


def test_get_default_date_range(monkeypatch):
    mock_dt = SimpleNamespace(now=lambda tz=None: datetime(2024, 5, 15))
    monkeypatch.setattr(attendance, "datetime", mock_dt)

    start, end = attendance.get_default_date_range()
    assert start == date(2024, 5, 1)
    assert end == date(2024, 5, 31)
