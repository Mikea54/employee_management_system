from datetime import datetime
from app import db


class PayPeriod(db.Model):
    __tablename__ = 'pay_periods'

    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    payment_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Open')
    is_thirteenth_month = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    timesheets = db.relationship('Timesheet', backref='pay_period', lazy='dynamic')
    payrolls = db.relationship('Payroll', backref='pay_period', lazy='dynamic')

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
    def total_gross(self) -> float:
        payrolls = self.payrolls
        if hasattr(payrolls, 'all'):
            try:
                payrolls = payrolls.all()
            except Exception:
                payrolls = []
        return sum(p.gross_pay for p in payrolls) if payrolls else 0.0

    def __repr__(self):
        return f'<PayPeriod {self.start_date} to {self.end_date}>'


class Timesheet(db.Model):
    __tablename__ = 'timesheets'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    pay_period_id = db.Column(db.Integer, db.ForeignKey('pay_periods.id'), nullable=False)
    status = db.Column(db.String(20), default='Draft')
    total_hours = db.Column(db.Float, default=0.0)
    submitted_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee', backref='timesheets')
    approver = db.relationship('User', backref='approved_timesheets')
    time_entries = db.relationship('TimeEntry', backref='timesheet', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Timesheet {self.employee_id} {self.pay_period_id}>'


class TimeEntry(db.Model):
    __tablename__ = 'time_entries'

    id = db.Column(db.Integer, primary_key=True)
    timesheet_id = db.Column(db.Integer, db.ForeignKey('timesheets.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, default=0.0, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<TimeEntry {self.timesheet_id} {self.date} {self.hours} hours>'
