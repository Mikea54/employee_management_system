from datetime import datetime, timedelta
from sqlalchemy import or_
from app import db
from .compensation import EmployeeCompensation

class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(250))

    employees = db.relationship('Employee', backref='department', lazy='dynamic')

    def __repr__(self):
        return f'<Department {self.name}>'


class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    job_title = db.Column(db.String(100))
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    hire_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Active')  # Active, Inactive, OnLeave, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # New fields
    is_manager = db.Column(db.Boolean, default=False)
    level = db.Column(db.String(50))
    education_level = db.Column(db.String(100))
    birth_date = db.Column(db.Date)
    employment_type = db.Column(db.String(20))

    # Benefits & Compensation
    healthcare_enrolled = db.Column(db.Boolean, default=False)
    healthcare_enrollment_date = db.Column(db.Date)
    is_401k_enrolled = db.Column(db.Boolean, default=False)
    k401_enrollment_date = db.Column(db.Date)
    cell_phone_stipend = db.Column(db.Float, default=0.0)

    # One-to-one relationship with User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=True)
    user = db.relationship('User', back_populates='employee')

    # Self-referential relationship for manager
    manager = db.relationship('Employee', remote_side=[id], backref=db.backref('subordinates', lazy='dynamic'))

    # Relationships
    documents = db.relationship('Document', backref='employee', lazy='dynamic')
    attendance_records = db.relationship('Attendance', backref='employee', lazy='dynamic')
    leave_requests = db.relationship('LeaveRequest', backref='employee', lazy='dynamic')
    dependents = db.relationship('Dependent', backref='employee', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        if self.birth_date:
            today = datetime.now().date()
            age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
            return age
        return None

    @property
    def current_compensation(self):
        return EmployeeCompensation.query.filter(
            EmployeeCompensation.employee_id == self.id,
            or_(
                EmployeeCompensation.end_date.is_(None),
                EmployeeCompensation.end_date >= datetime.now().date(),
            ),
        ).order_by(EmployeeCompensation.effective_date.desc()).first()

    @property
    def base_salary(self) -> float:
        compensation = self.current_compensation
        return compensation.base_salary if compensation else 0.0

    @property
    def salary_type(self) -> str:
        compensation = self.current_compensation
        return getattr(compensation, 'salary_type', 'Annual') if compensation else ''

    @property
    def years_of_service(self) -> int:
        if not self.hire_date:
            return 0
        today = datetime.now().date()
        years = today.year - self.hire_date.year
        if (today.month, today.day) < (self.hire_date.month, self.hire_date.day):
            years -= 1
        return years

    @property
    def healthcare_eligible_date(self):
        if not self.hire_date:
            return None
        return self.hire_date + timedelta(days=60)

    @property
    def is_healthcare_eligible(self) -> bool:
        eligible = self.healthcare_eligible_date
        return bool(eligible and datetime.now().date() >= eligible)

    @property
    def k401_eligible_date(self):
        if not self.hire_date:
            return None
        return self.hire_date + timedelta(days=180)

    @property
    def is_401k_eligible(self) -> bool:
        eligible = self.k401_eligible_date
        return bool(eligible and datetime.now().date() >= eligible)

    @property
    def k401_vesting_date(self):
        start = self.k401_enrollment_date or self.k401_eligible_date
        return start + timedelta(days=1095) if start else None

    @property
    def initials(self) -> str:
        first = self.first_name[0] if self.first_name else ''
        last = self.last_name[0] if self.last_name else ''
        return f"{first}{last}".upper()

    def __repr__(self):
        return f'<Employee {self.employee_id}: {self.full_name}>'


class Dependent(db.Model):
    __tablename__ = 'dependents'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    relationship = db.Column(db.String(50))
    healthcare_enrolled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Dependent {self.name}>'
