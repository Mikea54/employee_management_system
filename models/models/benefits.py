from datetime import datetime
from app import db


class Benefit(db.Model):
    __tablename__ = 'benefits'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    benefit_type = db.Column(db.String(50), nullable=False)
    employer_contribution = db.Column(db.Float)
    employer_contribution_percentage = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee_benefits = db.relationship('EmployeeBenefit', back_populates='benefit', lazy='dynamic')

    def __repr__(self):
        return f'<Benefit {self.name}>'


class EmployeeBenefit(db.Model):
    __tablename__ = 'employee_benefits'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    benefit_id = db.Column(db.Integer, db.ForeignKey('benefits.id'), nullable=False)
    enrollment_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    employee_contribution = db.Column(db.Float, default=0.0)
    employee_contribution_percentage = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee', backref='benefits')
    benefit = db.relationship('Benefit', back_populates='employee_benefits')

    def __repr__(self):
        return f'<EmployeeBenefit {self.employee.full_name}: {self.benefit.name}>'
