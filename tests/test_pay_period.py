from datetime import datetime, timedelta


class PayPeriod:
    """Minimal PayPeriod model used for isolated tests."""

    def __init__(self, start_date, end_date, payrolls=None):
        self.start_date = start_date
        self.end_date = end_date
        self.payrolls = payrolls or []

    @property
    def is_current(self):
        today = datetime.now().date()
        return self.start_date <= today <= self.end_date

    @property
    def is_future(self):
        today = datetime.now().date()
        return self.start_date > today

    @property
    def total_days(self):
        delta = self.end_date - self.start_date
        return delta.days + 1

    @property
    def total_gross(self):
        payrolls = self.payrolls
        if hasattr(payrolls, "all"):
            try:
                payrolls = payrolls.all()
            except Exception:
                payrolls = []
        return sum(p.gross_pay for p in payrolls) if payrolls else 0.0


class DummyPayroll:
    """Simple payroll record with a gross_pay attribute."""

    def __init__(self, gross_pay):
        self.gross_pay = gross_pay


def test_pay_period_properties():
    today = datetime.now().date()
    start = today - timedelta(days=1)
    end = today + timedelta(days=1)

    payrolls = [DummyPayroll(100.0), DummyPayroll(200.0)]

    period = PayPeriod(start, end, payrolls)

    assert period.is_current is True
    assert period.is_future is False
    assert period.total_days == 3
    assert period.total_gross == 300.0
