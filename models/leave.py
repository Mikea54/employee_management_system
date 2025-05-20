from datetime import datetime
from app import db


class LeaveType(db.Model):
    __tablename__ = 'leave_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(250))
    is_paid = db.Column(db.Boolean, default=True)

    leave_requests = db.relationship('LeaveRequest', backref='leave_type', lazy='dynamic')
    leave_balances = db.relationship('LeaveBalance', backref='leave_type', lazy='dynamic')

    def __repr__(self):
        return f'<LeaveType {self.name}>'


class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False, default=0)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending')
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approval_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    approver = db.relationship('User', backref='approved_leaves')

    def __repr__(self):
        return f'<LeaveRequest {self.employee_id} {self.start_date} to {self.end_date}>'


class LeaveBalance(db.Model):
    __tablename__ = 'leave_balances'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_days_deprecated = db.Column(db.Float)
    used_days_deprecated = db.Column(db.Float)
    total_hours = db.Column(db.Float, nullable=False, default=0)
    used_hours = db.Column(db.Float, default=0)
    accrual_rate = db.Column(db.Float, default=2.80)

    employee = db.relationship('Employee', backref='leave_balances')

    @property
    def remaining_hours(self):
        return self.total_hours - self.used_hours

    @property
    def remaining_days(self):
        return self.remaining_hours / 8.0

    @property
    def total_days(self):
        return self.total_hours / 8.0

    @property
    def used_days(self):
        return self.used_hours / 8.0

    def accrue_from_timesheet(self, hours_worked):
        if hours_worked <= 0:
            return 0
        hours_accrued = hours_worked * (self.accrual_rate / 40.0)
        self.total_hours += hours_accrued
        return hours_accrued

    def __repr__(self):
        return f'<LeaveBalance {self.employee_id} {self.leave_type_id} {self.year}: {self.remaining_hours} hours>'
