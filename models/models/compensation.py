from datetime import datetime
from app import db


class SalaryStructure(db.Model):
    __tablename__ = 'salary_structures'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    base_salary_min = db.Column(db.Float, nullable=False)
    base_salary_max = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    components = db.relationship('SalaryComponent', backref='salary_structure', lazy='dynamic')

    def __repr__(self):
        return f'<SalaryStructure {self.name}>'


class ComponentType:
    ALLOWANCE = 'allowance'
    BONUS = 'bonus'
    DEDUCTION = 'deduction'
    BENEFIT = 'benefit'
    TAX = 'tax'
    STIPEND = 'stipend'


class IncentiveType:
    BONUS = 'bonus'
    COMMISSION = 'commission'


class SalaryComponent(db.Model):
    __tablename__ = 'salary_components'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    component_type = db.Column(db.String(20), nullable=False)
    is_percentage = db.Column(db.Boolean, default=False)
    value = db.Column(db.Float, nullable=False)
    is_taxable = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    salary_structure_id = db.Column(db.Integer, db.ForeignKey('salary_structures.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SalaryComponent {self.name}>'


class EmployeeCompensation(db.Model):
    __tablename__ = 'employee_compensations'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    base_salary = db.Column(db.Float, nullable=False)
    salary_type = db.Column(db.String(20), default='Annual')
    hours_per_week = db.Column(db.Float, default=40.0)
    effective_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    salary_structure_id = db.Column(db.Integer, db.ForeignKey('salary_structures.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee', backref=db.backref('compensations', lazy='dynamic'))
    salary_structure = db.relationship('SalaryStructure')

    def __repr__(self):
        return f'<EmployeeCompensation {self.employee.full_name}: ${self.base_salary}>'


class EmployeeIncentive(db.Model):
    __tablename__ = 'employee_incentives'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    incentive_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_awarded = db.Column(db.Date, default=datetime.utcnow)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee', backref='incentives')

    def __repr__(self):
        return f'<EmployeeIncentive {self.employee_id} {self.incentive_type}: ${self.amount}>'


class CompensationReport(db.Model):
    __tablename__ = 'compensation_reports'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    name = db.Column(db.String(100))
    report_type = db.Column(db.String(20))
    include_benefits = db.Column(db.Boolean, default=False)
    include_bonuses = db.Column(db.Boolean, default=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    year = db.Column(db.Integer, nullable=False)
    generated_date = db.Column(db.DateTime, default=datetime.utcnow)
    base_salary = db.Column(db.Float, nullable=False)
    total_bonus = db.Column(db.Float, default=0.0)
    total_allowances = db.Column(db.Float, default=0.0)
    total_deductions = db.Column(db.Float, default=0.0)
    employer_benefit_contributions = db.Column(db.Float, default=0.0)
    total_compensation = db.Column(db.Float, nullable=False)
    report_file_path = db.Column(db.String(255))
    is_visible_to_employee = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee', backref='compensation_reports')
    department = db.relationship('Department')
    creator = db.relationship('User')

    def __repr__(self):
        return f'<CompensationReport {self.employee.full_name}: {self.year}>'
