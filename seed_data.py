from datetime import date
from app import app, db
from models import User, Role, Permission, Department, Employee, DocumentType, LeaveType, PayPeriod
from create_pay_periods import create_initial_pay_periods


def create_permissions():
    """Create standard permissions"""
    perms = [
        ("employee_view", "View Employees"),
        ("employee_edit", "Edit Employees"),
        ("attendance_manage", "Manage Attendance"),
        ("leave_approve", "Approve Leave Requests"),
        ("document_manage", "Manage Documents"),
        ("user_manage", "Manage Users"),
        ("system_admin", "System Administration"),
    ]

    for name, desc in perms:
        if not Permission.query.filter_by(name=name).first():
            db.session.add(Permission(name=name, description=desc))
    db.session.commit()
    print("Permissions created successfully.")

def create_seed_data():
    """Creates initial seed data for the application"""
    with app.app_context():
        # Check if there's already basic data
        if Role.query.count() > 0 and User.query.count() > 0:
            # Check if we need to add document types
            if DocumentType.query.count() == 0:
                print("Adding document types...")
                create_document_types()
            
            # Check if we need to add leave types
            if LeaveType.query.count() == 0:
                print("Adding leave types...")
                create_leave_types()
            else:
                print("All seed data already exists. Skipping.")
            return
        
        print("Creating seed data...")

        # Create base permissions
        create_permissions()
        
        # Create roles if they don't already exist
        roles_to_add = []

        admin_role = Role.query.filter_by(name="Admin").first()
        if not admin_role:
            admin_role = Role(name="Admin", description="Administrator with full access")
            roles_to_add.append(admin_role)

        hr_role = Role.query.filter_by(name="HR").first()
        if not hr_role:
            hr_role = Role(name="HR", description="Human Resources staff")
            roles_to_add.append(hr_role)

        manager_role = Role.query.filter_by(name="Manager").first()
        if not manager_role:
            manager_role = Role(name="Manager", description="Department manager")
            roles_to_add.append(manager_role)

        employee_role = Role.query.filter_by(name="Employee").first()
        if not employee_role:
            employee_role = Role(name="Employee", description="Regular employee")
            roles_to_add.append(employee_role)

        if roles_to_add:
            db.session.add_all(roles_to_add)
            db.session.commit()

        # Assign permissions to roles without creating duplicates
        perms = {p.name: p for p in Permission.query.all()}

        def assign_permissions(role, permissions):
            for perm in permissions:
                if perm and not role.permissions.filter_by(id=perm.id).first():
                    role.permissions.append(perm)

        assign_permissions(admin_role, perms.values())
        assign_permissions(hr_role, [
            perms.get('employee_view'),
            perms.get('employee_edit'),
            perms.get('attendance_manage'),
            perms.get('leave_approve'),
            perms.get('document_manage'),
            perms.get('user_manage'),
        ])
        assign_permissions(manager_role, [
            perms.get('employee_view'),
            perms.get('attendance_manage'),
            perms.get('leave_approve'),
        ])

        db.session.commit()
        
        # Create departments if they don't already exist
        admin_dept = Department.query.filter_by(name="Administration").first()
        if not admin_dept:
            admin_dept = Department(
                name="Administration", description="Administration and management"
            )
            db.session.add(admin_dept)

        hr_dept = Department.query.filter_by(name="Human Resources").first()
        if not hr_dept:
            hr_dept = Department(name="Human Resources", description="HR department")
            db.session.add(hr_dept)

        it_dept = Department.query.filter_by(name="Information Technology").first()
        if not it_dept:
            it_dept = Department(
                name="Information Technology", description="IT department"
            )
            db.session.add(it_dept)

        db.session.commit()
        
        # Create document types
        create_document_types()
        
        # Create leave types
        create_leave_types()

        
        # Create admin employee
        admin_employee = Employee(
            employee_id="EMP001",
            first_name="Admin",
            last_name="User",
            email="admin@example.com",
            phone="555-123-4567",
            address="123 Admin St, Admin City",
            department_id=admin_dept.id,
            job_title="System Administrator",
            hire_date=date.today(),
            status="Active"
        )
        
        db.session.add(admin_employee)
        db.session.commit()
        
        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@example.com",
            role_id=admin_role.id,
            is_active=True
        )
        admin_user.set_password("admin123")
        
        db.session.add(admin_user)
        db.session.commit()
        
        # Link admin user to admin employee
        admin_employee.user_id = admin_user.id
        db.session.commit()
        
        print("Seed data created successfully!")
        print("Admin login credentials:")
        print("Username: admin")
        print("Password: admin123")

def create_document_types():
    """Create standard document types if missing."""

    existing = {dt.name for dt in DocumentType.query.all()}
    to_create = []

    def add_if_missing(name: str, description: str) -> None:
        if name not in existing:
            to_create.append(DocumentType(name=name, description=description, is_active=True))

    add_if_missing("Employment Contract", "Official employment contracts and agreements")
    add_if_missing("Professional Certification", "Professional qualifications and certifications")
    add_if_missing("Performance Review", "Employee performance assessments and evaluations")
    add_if_missing("ID Document", "Identification documents and official credentials")
    add_if_missing("Tax Document", "Tax forms and related financial documents")

    if not to_create:
        print("Document types already exist. Skipping.")
        return

    db.session.add_all(to_create)
    db.session.commit()
    print("Document types created successfully.")

def create_leave_types():
    """Create standard leave types if missing."""
    existing = {lt.name for lt in LeaveType.query.all()}
    to_create = []

    def add_if_missing(name: str, description: str, is_paid: bool) -> None:
        if name not in existing:
            to_create.append(LeaveType(name=name, description=description, is_paid=is_paid))

    add_if_missing("Annual Leave", "Regular paid vacation leave", True)
    add_if_missing("Sick Leave", "Leave for illness or medical appointments", True)
    add_if_missing("Personal Leave", "Leave for personal matters", True)
    add_if_missing("Parental Leave", "Leave for new parents (maternity/paternity)", True)
    add_if_missing("Unpaid Leave", "Leave without pay for extended absences", False)
    add_if_missing("Bereavement Leave", "Leave for family loss or funeral attendance", True)

    if not to_create:
        print("Leave types already exist. Skipping.")
        return

    db.session.add_all(to_create)
    db.session.commit()
    print("Leave types created successfully.")

if __name__ == "__main__":
    create_seed_data()
