from datetime import date
from app import app, db
from models import User, Role, Permission, Department, Employee, DocumentType, LeaveType

def create_document_types():
    """Create standard document types"""
    # Create document types
    contract_type = DocumentType(
        name="Employment Contract",
        description="Official employment contracts and agreements",
        is_active=True
    )
    
    certification_type = DocumentType(
        name="Professional Certification",
        description="Professional qualifications and certifications",
        is_active=True
    )
    
    review_type = DocumentType(
        name="Performance Review",
        description="Employee performance assessments and evaluations",
        is_active=True
    )
    
    id_type = DocumentType(
        name="ID Document",
        description="Identification documents and official credentials",
        is_active=True
    )
    
    tax_type = DocumentType(
        name="Tax Document",
        description="Tax forms and related financial documents",
        is_active=True
    )
    
    db.session.add_all([contract_type, certification_type, review_type, id_type, tax_type])
    db.session.commit()
    print("Document types created successfully.")


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
        
        # Create roles
        admin_role = Role(name="Admin", description="Administrator with full access")
        hr_role = Role(name="HR", description="Human Resources staff")
        manager_role = Role(name="Manager", description="Department manager")
        employee_role = Role(name="Employee", description="Regular employee")
        
        db.session.add_all([admin_role, hr_role, manager_role, employee_role])
        db.session.commit()

        # Assign permissions to roles
        perms = {p.name: p for p in Permission.query.all()}
        admin_role.permissions.extend(perms.values())
        hr_role.permissions.extend([p for p in [
            perms.get('employee_view'),
            perms.get('employee_edit'),
            perms.get('attendance_manage'),
            perms.get('leave_approve'),
            perms.get('document_manage'),
            perms.get('user_manage'),
        ] if p])
        manager_role.permissions.extend([p for p in [
            perms.get('employee_view'),
            perms.get('attendance_manage'),
            perms.get('leave_approve'),
        ] if p])
        db.session.commit()
        
        # Create departments
        admin_dept = Department(name="Administration", description="Administration and management")
        hr_dept = Department(name="Human Resources", description="HR department")
        it_dept = Department(name="Information Technology", description="IT department")
        
        db.session.add_all([admin_dept, hr_dept, it_dept])
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
    """Create standard document types"""
    # Create document types
    contract_type = DocumentType(
        name="Employment Contract",
        description="Official employment contracts and agreements",
        is_active=True
    )
    
    certification_type = DocumentType(
        name="Professional Certification",
        description="Professional qualifications and certifications",
        is_active=True
    )
    
    review_type = DocumentType(
        name="Performance Review",
        description="Employee performance assessments and evaluations",
        is_active=True
    )
    
    id_type = DocumentType(
        name="ID Document",
        description="Identification documents and official credentials",
        is_active=True
    )
    
    tax_type = DocumentType(
        name="Tax Document",
        description="Tax forms and related financial documents",
        is_active=True
    )
    
    db.session.add_all([contract_type, certification_type, review_type, id_type, tax_type])
    db.session.commit()
    print("Document types created successfully.")

def create_leave_types():
    """Create standard leave types"""
    # Create leave types
    annual_leave = LeaveType(
        name="Annual Leave",
        description="Regular paid vacation leave",
        is_paid=True
    )
    
    sick_leave = LeaveType(
        name="Sick Leave",
        description="Leave for illness or medical appointments",
        is_paid=True
    )
    
    personal_leave = LeaveType(
        name="Personal Leave",
        description="Leave for personal matters",
        is_paid=True
    )
    
    parental_leave = LeaveType(
        name="Parental Leave",
        description="Leave for new parents (maternity/paternity)",
        is_paid=True
    )
    
    unpaid_leave = LeaveType(
        name="Unpaid Leave",
        description="Leave without pay for extended absences",
        is_paid=False
    )
    
    bereavement_leave = LeaveType(
        name="Bereavement Leave",
        description="Leave for family loss or funeral attendance",
        is_paid=True
    )
    
    db.session.add_all([annual_leave, sick_leave, personal_leave, parental_leave, unpaid_leave, bereavement_leave])
    db.session.commit()
    print("Leave types created successfully.")

if __name__ == "__main__":
    create_seed_data()
