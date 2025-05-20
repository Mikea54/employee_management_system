from datetime import datetime
from app import db


class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Draft')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = db.relationship('Department')
    creator = db.relationship('User')
    items = db.relationship('BudgetItem', backref='budget', lazy='dynamic')

    def __repr__(self):
        return f'<Budget {self.name}: {self.year}>'


class BudgetCategory:
    SALARIES = 'salaries'
    BONUSES = 'bonuses'
    BENEFITS = 'benefits'
    STIPENDS = 'stipends'
    TAXES = 'taxes'
    INSURANCE = 'insurance'


class BudgetItem(db.Model):
    __tablename__ = 'budget_items'

    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50))
    description = db.Column(db.Text)
    amount = db.Column(db.Float, nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee')

    def __repr__(self):
        return f'<BudgetItem {self.category}: ${self.amount}>'
