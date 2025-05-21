from datetime import datetime
from app import db


class Payroll(db.Model):
    __tablename__ = 'payrolls'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    pay_period_id = db.Column(db.Integer, db.ForeignKey('pay_periods.id'), nullable=False)
    gross_pay = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, default=0.0, nullable=False)
    total_deductions = db.Column(db.Float, default=0.0, nullable=False)
    net_pay = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Draft')
    payslip_generated = db.Column(db.Boolean, default=False)
    payslip_sent = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee', backref='payrolls')
    entries = db.relationship('PayrollEntry', back_populates='payroll', lazy='dynamic')

    def __repr__(self):
        return f'<Payroll {self.employee.full_name}: {self.pay_period.start_date} to {self.pay_period.end_date}>'


class PayrollEntry(db.Model):
    __tablename__ = 'payroll_entries'

    id = db.Column(db.Integer, primary_key=True)
    payroll_id = db.Column(db.Integer, db.ForeignKey('payrolls.id'), nullable=False)
    component_name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    is_recurring = db.Column(db.Boolean, default=True)
    is_manual_adjustment = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    payroll = db.relationship('Payroll', back_populates='entries')
    payroll_obj = db.relationship('Payroll', overlaps='payroll,entries')

    def __repr__(self):
        return f'<PayrollEntry {self.component_name}: ${self.amount}>'
