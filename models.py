from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Association table between roles and permissions
role_permissions = db.Table(
    'role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

# Define user roles
class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(250))
    
    users = db.relationship('User', backref='role', lazy='dynamic')
    permissions = db.relationship('Permission', secondary=role_permissions, backref='roles', lazy='dynamic')

    def has_permission(self, perm_name: str) -> bool:
        """Check if role has the specified permission."""
        return any(p.name == perm_name for p in self.permissions)
    
    def __repr__(self):
        return f'<Role {self.name}>'


# Permission model
class Permission(db.Model):
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Permission {self.name}>'

# Define departments
class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(250))
    
    employees = db.relationship('Employee', backref='department', lazy='dynamic')
    
    def __repr__(self):
        return f'<Department {self.name}>'

# User model for authentication
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    theme_preference = db.Column(db.String(20), default='dark')  # 'dark' or 'light'
    
    # One-to-one relationship with Employee
    employee = db.relationship('Employee', uselist=False, back_populates='user')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_theme(self):
        return self.theme_preference or 'dark'
        
    def toggle_theme(self):
        if self.theme_preference == 'dark':
            self.theme_preference = 'light'
        else:
            self.theme_preference = 'dark'
        return self.theme_preference
    
    def has_role(self, roles):
        """Check if user has one of the specified roles
        
        Args:
            roles: A list of role names or a single role name
            
        Returns:
            bool: True if user has one of the specified roles
        """
        if not self.role:
            return False
            
        if isinstance(roles, list):
            return self.role.name in roles
        else:
            return self.role.name == roles

    def has_permission(self, perm_name: str) -> bool:
        """Check if the user's role includes the given permission."""
        if not self.role:
            return False
        return self.role.has_permission(perm_name)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Employee model
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
    status = db.Column(db.String(20), default='Active')  # Active, Inactive, On Leave, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # New fields
    is_manager = db.Column(db.Boolean, default=False)  # Checkbox to mark as manager
    level = db.Column(db.String(50))  # Employee level (e.g., Entry, Associate, Senior, Lead, etc.)
    education_level = db.Column(db.String(100))  # Highest education achieved
    birth_date = db.Column(db.Date)  # Date of birth
    employment_type = db.Column(db.String(20))  # Full-time, Part-time, Consultant
    
    # One-to-one relationship with User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=True)
    user = db.relationship('User', back_populates='employee')
    
    # Self-referential relationship for manager
    manager = db.relationship('Employee', remote_side=[id], backref=db.backref('subordinates', lazy='dynamic'))
    
    # Relationships
    documents = db.relationship('Document', backref='employee', lazy='dynamic')
    attendance_records = db.relationship('Attendance', backref='employee', lazy='dynamic')
    leave_requests = db.relationship('LeaveRequest', backref='employee', lazy='dynamic')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        """Calculate age based on birth_date"""
        if self.birth_date:
            today = datetime.now().date()
            age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
            return age
        return None

    @property
    def current_compensation(self):
        """Return the employee's active compensation record."""
        from sqlalchemy import or_
        return EmployeeCompensation.query.filter(
            EmployeeCompensation.employee_id == self.id,
            or_(
                EmployeeCompensation.end_date.is_(None),
                EmployeeCompensation.end_date >= datetime.now().date(),
            ),
        ).order_by(EmployeeCompensation.effective_date.desc()).first()

    @property
    def base_salary(self) -> float:
        """Convenience access to the employee's current base salary."""
        compensation = self.current_compensation
        return compensation.base_salary if compensation else 0.0

    @property
    def salary_type(self) -> str:
        """Return 'Annual' or 'Hourly' based on current compensation."""
        compensation = self.current_compensation
        return getattr(compensation, 'salary_type', 'Annual') if compensation else ''

    @property
    def years_of_service(self) -> int:
        """Number of full years since hire date."""
        if not self.hire_date:
            return 0
        today = datetime.now().date()
        years = today.year - self.hire_date.year
        if (today.month, today.day) < (self.hire_date.month, self.hire_date.day):
            years -= 1
        return years

    @property
    def initials(self) -> str:
        """Initials used in avatar placeholders."""
        first = self.first_name[0] if self.first_name else ''
        last = self.last_name[0] if self.last_name else ''
        return f"{first}{last}".upper()
    
    def __repr__(self):
        return f'<Employee {self.employee_id}: {self.full_name}>'

# Document Type model
class DocumentType(db.Model):
    __tablename__ = 'document_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Removed relationship with Document since document_type_id doesn't exist in DB
    creator = db.relationship('User', backref='created_document_types')
    
    def __repr__(self):
        return f'<DocumentType {self.name}>'

# Document model
class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(50))  # This is the only document type field in the DB
    description = db.Column(db.Text)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    uploader = db.relationship('User', backref='uploaded_documents')
    
    def __repr__(self):
        return f'<Document {self.title}>'

# Attendance model
class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    clock_in = db.Column(db.DateTime)
    clock_out = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # Present, Absent, Half-day, etc.
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Attendance {self.employee_id} {self.date}>'

# Leave types
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

# Leave request model
class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False, default=0)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approval_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    approver = db.relationship('User', backref='approved_leaves')
    
    def __repr__(self):
        return f'<LeaveRequest {self.employee_id} {self.start_date} to {self.end_date}>'

# Leave balance model
class LeaveBalance(db.Model):
    __tablename__ = 'leave_balances'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey('leave_types.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_days_deprecated = db.Column(db.Float)  # Kept for backward compatibility
    used_days_deprecated = db.Column(db.Float)   # Kept for backward compatibility
    total_hours = db.Column(db.Float, nullable=False, default=0)
    used_hours = db.Column(db.Float, default=0)
    accrual_rate = db.Column(db.Float, default=2.80)  # Hours accrued per 40 hours worked
    
    employee = db.relationship('Employee', backref='leave_balances')
    
    @property
    def remaining_hours(self):
        return self.total_hours - self.used_hours
    
    @property
    def remaining_days(self):  # Kept for backward compatibility
        return self.remaining_hours / 8.0
    
    @property
    def total_days(self):  # Kept for backward compatibility
        return self.total_hours / 8.0
    
    @property
    def used_days(self):  # Kept for backward compatibility
        return self.used_hours / 8.0
    
    def accrue_from_timesheet(self, hours_worked):
        """Accrue leave based on hours worked (typically from a timesheet).
        Formula: hours_accrued = hours_worked * (accrual_rate / 40)
        """
        if hours_worked <= 0:
            return 0
            
        hours_accrued = hours_worked * (self.accrual_rate / 40.0)
        self.total_hours += hours_accrued
        return hours_accrued
    
    def __repr__(self):
        return f'<LeaveBalance {self.employee_id} {self.leave_type_id} {self.year}: {self.remaining_hours} hours>'

# Pay Period model
class PayPeriod(db.Model):
    __tablename__ = 'pay_periods'
    
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    payment_date = db.Column(db.Date)  # Optional payroll payment date
    status = db.Column(db.String(20), default='Open')  # Open, Closed, Processing, Draft, Completed
    is_thirteenth_month = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    timesheets = db.relationship('Timesheet', backref='pay_period', lazy='dynamic')
    payrolls = db.relationship('Payroll', backref='pay_period', lazy='dynamic')
    
    @property
    def is_current(self):
        """Check if the current date falls within this pay period"""
        today = datetime.now().date()
        return self.start_date <= today <= self.end_date

    @property
    def is_future(self):
        """Check if this pay period is in the future."""
        today = datetime.now().date()
        return self.start_date > today
    
    @property
    def total_days(self):
        """Calculate the total working days in this pay period"""
        delta = self.end_date - self.start_date
        return delta.days + 1

    @property
    def total_gross(self) -> float:
        """Sum of gross pay from all payrolls in this period."""
        # self.payrolls is a dynamic relationship returning a Query when
        # attached to a session. When detached (e.g., in tests), it may be a
        # simple list. Support both scenarios.
        payrolls = self.payrolls
        if hasattr(payrolls, "all"):
            try:
                payrolls = payrolls.all()
            except Exception:
                payrolls = []
        return sum(p.gross_pay for p in payrolls) if payrolls else 0.0
    
    def __repr__(self):
        return f'<PayPeriod {self.start_date} to {self.end_date}>'

# Timesheet model
class Timesheet(db.Model):
    __tablename__ = 'timesheets'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    pay_period_id = db.Column(db.Integer, db.ForeignKey('pay_periods.id'), nullable=False)
    status = db.Column(db.String(20), default='Draft')  # Draft, Submitted, Approved, Rejected
    total_hours = db.Column(db.Float, default=0.0)
    submitted_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    employee = db.relationship('Employee', backref='timesheets')
    approver = db.relationship('User', backref='approved_timesheets')
    time_entries = db.relationship('TimeEntry', backref='timesheet', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Timesheet {self.employee_id} {self.pay_period_id}>'

# Time Entry model
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

# Salary Structure model
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
    
    # Relationships
    components = db.relationship('SalaryComponent', backref='salary_structure', lazy='dynamic')
    
    def __repr__(self):
        return f'<SalaryStructure {self.name}>'

# Salary Component Types Enum
class ComponentType:
    ALLOWANCE = 'allowance'
    BONUS = 'bonus'
    DEDUCTION = 'deduction'
    BENEFIT = 'benefit'
    TAX = 'tax'
    STIPEND = 'stipend'

# Salary Component model
class SalaryComponent(db.Model):
    __tablename__ = 'salary_components'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    component_type = db.Column(db.String(20), nullable=False)  # allowance, bonus, deduction, benefit, tax, stipend
    is_percentage = db.Column(db.Boolean, default=False)
    value = db.Column(db.Float, nullable=False)  # Fixed amount or percentage based on is_percentage
    is_taxable = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    salary_structure_id = db.Column(db.Integer, db.ForeignKey('salary_structures.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # No relationships anymore as PayrollEntry now uses component_name field
    
    def __repr__(self):
        return f'<SalaryComponent {self.name}>'

# Employee Compensation model
class EmployeeCompensation(db.Model):
    __tablename__ = 'employee_compensations'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    base_salary = db.Column(db.Float, nullable=False)
    salary_type = db.Column(db.String(20), default='Annual')  # 'Annual' or 'Hourly'
    effective_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)  # NULL means currently active
    salary_structure_id = db.Column(db.Integer, db.ForeignKey('salary_structures.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', backref='compensations')
    salary_structure = db.relationship('SalaryStructure')
    
    def __repr__(self):
        return f'<EmployeeCompensation {self.employee.full_name}: ${self.base_salary}>'


# Payroll model (payslip)
class Payroll(db.Model):
    __tablename__ = 'payrolls'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    pay_period_id = db.Column(db.Integer, db.ForeignKey('pay_periods.id'), nullable=False)
    gross_pay = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, default=0.0, nullable=False)
    total_deductions = db.Column(db.Float, default=0.0, nullable=False)
    net_pay = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Draft')  # Draft, Approved, Paid
    payslip_generated = db.Column(db.Boolean, default=False)
    payslip_sent = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', backref='payrolls')
    entries = db.relationship(
        'PayrollEntry', back_populates='payroll', lazy='dynamic'
    )
    
    def __repr__(self):
        return f'<Payroll {self.employee.full_name}: {self.pay_period.start_date} to {self.pay_period.end_date}>'

# Payroll Entry model (payslip details)
class PayrollEntry(db.Model):
    __tablename__ = 'payroll_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    payroll_id = db.Column(db.Integer, db.ForeignKey('payrolls.id'), nullable=False)
    component_name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # Earning, Deduction
    amount = db.Column(db.Float, nullable=False)
    is_recurring = db.Column(db.Boolean, default=True)
    is_manual_adjustment = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Reference to parent Payroll
    payroll = db.relationship('Payroll', back_populates='entries')
    payroll_obj = db.relationship('Payroll', overlaps='payroll,entries')
    
    def __repr__(self):
        return f'<PayrollEntry {self.component_name}: ${self.amount}>'

# Benefits model
class Benefit(db.Model):
    __tablename__ = 'benefits'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    benefit_type = db.Column(db.String(50), nullable=False)  # Health, Dental, Vision, 401K, etc.
    employer_contribution = db.Column(db.Float)  # Fixed amount or NULL
    employer_contribution_percentage = db.Column(db.Float)  # Percentage or NULL
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee_benefits = db.relationship('EmployeeBenefit', back_populates='benefit', lazy='dynamic')
    
    def __repr__(self):
        return f'<Benefit {self.name}>'

# Employee Benefits model
class EmployeeBenefit(db.Model):
    __tablename__ = 'employee_benefits'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    benefit_id = db.Column(db.Integer, db.ForeignKey('benefits.id'), nullable=False)
    enrollment_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)  # NULL means currently active
    employee_contribution = db.Column(db.Float, default=0.0)
    employee_contribution_percentage = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', backref='benefits')
    benefit = db.relationship('Benefit', back_populates='employee_benefits')
    
    def __repr__(self):
        return f'<EmployeeBenefit {self.employee.full_name}: {self.benefit.name}>'

# Budget model
class Budget(db.Model):
    __tablename__ = 'budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Draft')  # Draft, Approved, Closed
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    department = db.relationship('Department')
    creator = db.relationship('User')
    items = db.relationship('BudgetItem', backref='budget', lazy='dynamic')
    
    def __repr__(self):
        return f'<Budget {self.name}: {self.year}>'

# Budget Category Enum
class BudgetCategory:
    SALARIES = 'salaries'
    BONUSES = 'bonuses'
    BENEFITS = 'benefits'
    STIPENDS = 'stipends'
    TAXES = 'taxes'
    INSURANCE = 'insurance'

# Budget Item model
class BudgetItem(db.Model):
    __tablename__ = 'budget_items'
    
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50))
    description = db.Column(db.Text)
    amount = db.Column(db.Float, nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))  # For employee-specific budget items
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee')
    
    def __repr__(self):
        return f'<BudgetItem {self.category}: ${self.amount}>'

# Compensation Report model
class CompensationReport(db.Model):
    __tablename__ = 'compensation_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    generated_date = db.Column(db.DateTime, default=datetime.utcnow)
    base_salary = db.Column(db.Float, nullable=False)
    total_bonus = db.Column(db.Float, default=0.0)
    total_allowances = db.Column(db.Float, default=0.0)
    total_deductions = db.Column(db.Float, default=0.0)
    employer_benefit_contributions = db.Column(db.Float, default=0.0)
    total_compensation = db.Column(db.Float, nullable=False)
    report_file_path = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', backref='compensation_reports')
    creator = db.relationship('User')
    
    def __repr__(self):
        return f'<CompensationReport {self.employee.full_name}: {self.year}>'
