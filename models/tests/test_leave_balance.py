class LeaveBalance:
    def __init__(self, total_hours=0.0, accrual_rate=2.80):
        self.total_hours = total_hours
        self.accrual_rate = accrual_rate

    def accrue_from_timesheet(self, hours_worked: float) -> float:
        """Accrue leave based on hours worked."""
        if hours_worked <= 0:
            return 0
        hours_accrued = hours_worked * (self.accrual_rate / 40.0)
        self.total_hours += hours_accrued
        return hours_accrued

def test_accrue_from_timesheet():
    lb = LeaveBalance(total_hours=0, accrual_rate=2.80)
    # Positive hours accrue leave
    assert lb.accrue_from_timesheet(40) == 2.8
    assert lb.total_hours == 2.8
    # Negative hours should not accrue leave
    assert lb.accrue_from_timesheet(-5) == 0
    assert lb.total_hours == 2.8
