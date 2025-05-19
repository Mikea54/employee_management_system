from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import os
from app import db
from models import Employee, Department, User, Role, Attendance
from utils.helpers import role_required
from utils.importers import process_employee_import, get_import_template

employee_bp = Blueprint('employees', __name__, url_prefix='/employees')

def get_employee_navigation(current_id):
    """Get next and previous employee IDs for navigation
    
    Args:
        current_id: The ID of the current employee being viewed
        
    Returns:
        Dictionary with prev_id and next_id
    """
    # Get all employees ordered by ID (could also order by name if preferred)
    all_employees = Employee.query.order_by(Employee.last_name, Employee.first_name).all()
    employee_ids = [e.id for e in all_employees]
    
    if current_id not in employee_ids:
        return {'prev_id': None, 'next_id': None}
    
    current_index = employee_ids.index(current_id)
    prev_id = employee_ids[current_index - 1] if current_index > 0 else None
    next_id = employee_ids[current_index + 1] if current_index < len(employee_ids) - 1 else None
    
    return {
        'prev_id': prev_id,
        'next_id': next_id,
        'total_count': len(employee_ids),
        'current_position': current_index + 1  # 1-based index for display
    }

@employee_bp.route('/')
@login_required
@role_required('Admin', 'HR', 'Manager')
def list_employees():
    # Get filter parameters
    department_id = request.args.get('department', type=int)
    manager_id = request.args.get('manager')
    status = request.args.get('status')
    search_term = request.args.get('search')
    
    # Base query
    query = Employee.query
    
    # Apply filters
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    
    # Handle manager filter
    if manager_id:
        if manager_id == 'none':
            # Filter for employees with no manager
            query = query.filter(Employee.manager_id.is_(None))
        else:
            # Convert to integer for database lookup
            try:
                manager_id_int = int(manager_id)
                query = query.filter(Employee.manager_id == manager_id_int)
            except (ValueError, TypeError):
                pass  # Invalid manager_id, ignore this filter
    
    if status:
        query = query.filter(Employee.status == status)
    
    if search_term:
        search_term = f"%{search_term}%"
        query = query.filter(
            (Employee.first_name.ilike(search_term)) |
            (Employee.last_name.ilike(search_term)) |
            (Employee.email.ilike(search_term)) |
            (Employee.employee_id.ilike(search_term))
        )
    
    # Get employees
    employees = query.all()
    
    # Get departments for filter
    departments = Department.query.all()
    
    # Get managers for filter (using is_manager flag)
    managers = Employee.query.filter_by(is_manager=True).all()
    
    return render_template(
        'employees/list.html',
        employees=employees,
        departments=departments,
        managers=managers,
        current_filters={
            'department_id': department_id,
            'manager_id': manager_id,
            'status': status,
            'search_term': request.args.get('search', '')
        }
    )

@employee_bp.route('/<int:id>')
@login_required
def view_profile(id):
    employee = Employee.query.get_or_404(id)
    
    # Check permissions: Admin/HR can view all, Managers can view their subordinates, Employees can only view themselves
    if current_user.role.name not in ['Admin', 'HR']:
        if current_user.role.name == 'Manager':
            # Check if employee is a subordinate
            subordinate_ids = [emp.id for emp in current_user.employee.subordinates]
            if employee.id not in subordinate_ids and employee.id != current_user.employee.id:
                flash('You do not have permission to view this employee profile.', 'danger')
                return redirect(url_for('dashboard.index'))
        elif current_user.employee.id != id:
            flash('You do not have permission to view this employee profile.', 'danger')
            return redirect(url_for('dashboard.index'))
    
    # Get next and previous employee IDs for navigation
    nav_data = get_employee_navigation(id)
    
    # Pass models to the template as well
    import models as models_module
    return render_template('employees/profile.html', employee=employee, Attendance=Attendance, nav_data=nav_data, models=models_module)

@employee_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def create_employee():
    if request.method == 'POST':
        try:
            # Check if creating new department
            if request.form.get('create_new_department'):
                new_dept_name = request.form.get('new_department_name')
                new_dept_desc = request.form.get('new_department_description', '')
                
                if not new_dept_name:
                    flash('Department name is required when creating a new department.', 'danger')
                    departments = Department.query.all()
                    managers = Employee.query.filter_by(status='Active').order_by(Employee.last_name).all()
                    return render_template('employees/edit.html', 
                                          employee=None, 
                                          departments=departments, 
                                          managers=managers,
                                          is_new=True)
                
                # Check if department already exists
                existing_dept = Department.query.filter_by(name=new_dept_name).first()
                if existing_dept:
                    flash(f'Department "{new_dept_name}" already exists.', 'warning')
                    department_id = existing_dept.id
                else:
                    # Create new department
                    new_dept = Department(
                        name=new_dept_name,
                        description=new_dept_desc
                    )
                    db.session.add(new_dept)
                    db.session.flush()  # Get ID without committing
                    department_id = new_dept.id
                    flash(f'New department "{new_dept_name}" created successfully!', 'success')
            else:
                department_id = request.form.get('department_id', type=int)

            # Extract form data
            employee_data = {
                'employee_id': request.form.get('employee_id'),
                'first_name': request.form.get('first_name'),
                'last_name': request.form.get('last_name'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'address': request.form.get('address'),
                'department_id': department_id,
                'job_title': request.form.get('job_title'),
                'manager_id': request.form.get('manager_id', type=int) or None,
                'hire_date': datetime.strptime(request.form.get('hire_date'), '%Y-%m-%d').date(),
                'status': request.form.get('status', 'Active'),
                'is_manager': bool(request.form.get('is_manager')),  # Checkbox returns 'on' if checked or None if not
                'level': request.form.get('level'),
                'education_level': request.form.get('education_level')
            }
            
            # Handle birth_date if provided
            birth_date = request.form.get('birth_date')
            if birth_date:
                employee_data['birth_date'] = datetime.strptime(birth_date, '%Y-%m-%d').date()
            
            # Validate required fields
            required_fields = ['employee_id', 'first_name', 'last_name', 'email', 'department_id', 'job_title', 'hire_date']
            missing_fields = [field for field in required_fields if not employee_data.get(field)]
            
            if missing_fields:
                flash(f"Missing required fields: {', '.join(missing_fields)}", 'danger')
                return redirect(url_for('employees.create_employee'))
            
            # Check if employee_id or email already exists
            existing_employee = Employee.query.filter(
                (Employee.employee_id == employee_data['employee_id']) | 
                (Employee.email == employee_data['email'])
            ).first()
            
            if existing_employee:
                flash('An employee with this ID or email already exists.', 'danger')
                return redirect(url_for('employees.create_employee'))
            
            # Create employee
            new_employee = Employee(**employee_data)
            db.session.add(new_employee)
            db.session.commit()
            
            flash('Employee created successfully!', 'success')
            return redirect(url_for('employees.view_profile', id=new_employee.id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error creating employee: {str(e)}', 'danger')
    
    # Get departments and all active employees for form
    departments = Department.query.all()
    managers = Employee.query.filter_by(status='Active').order_by(Employee.last_name, Employee.first_name).all()
    
    return render_template('employees/edit.html', 
                          employee=None, 
                          departments=departments, 
                          managers=managers,
                          is_new=True)

@employee_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def edit_employee(id):
    employee = Employee.query.get_or_404(id)
    
    # Get next and previous employee IDs for navigation
    nav_data = get_employee_navigation(id)
    
    if request.method == 'POST':
        try:
            # Check if creating new department
            if request.form.get('create_new_department'):
                new_dept_name = request.form.get('new_department_name')
                new_dept_desc = request.form.get('new_department_description', '')
                
                if not new_dept_name:
                    flash('Department name is required when creating a new department.', 'danger')
                    departments = Department.query.all()
                    managers = Employee.query.filter_by(status='Active').all()
                    return render_template('employees/edit.html', 
                                          employee=employee, 
                                          departments=departments, 
                                          managers=managers,
                                          is_new=False)
                
                # Check if department already exists
                existing_dept = Department.query.filter_by(name=new_dept_name).first()
                if existing_dept:
                    flash(f'Department "{new_dept_name}" already exists.', 'warning')
                    department_id = existing_dept.id
                else:
                    # Create new department
                    new_dept = Department(
                        name=new_dept_name,
                        description=new_dept_desc
                    )
                    db.session.add(new_dept)
                    db.session.flush()  # Get ID without committing
                    department_id = new_dept.id
                    flash(f'New department "{new_dept_name}" created successfully!', 'success')
            else:
                department_id = request.form.get('department_id', type=int)
    
            # Update employee data
            employee.first_name = request.form.get('first_name')
            employee.last_name = request.form.get('last_name')
            employee.email = request.form.get('email')
            employee.phone = request.form.get('phone')
            employee.address = request.form.get('address')
            employee.department_id = department_id
            employee.job_title = request.form.get('job_title')
            employee.manager_id = request.form.get('manager_id', type=int) or None
            employee.status = request.form.get('status')
            
            # Update new fields
            employee.is_manager = bool(request.form.get('is_manager'))
            employee.level = request.form.get('level')
            employee.education_level = request.form.get('education_level')
            
            # Handle dates
            new_hire_date = request.form.get('hire_date')
            if new_hire_date:
                employee.hire_date = datetime.strptime(new_hire_date, '%Y-%m-%d').date()
                
            birth_date = request.form.get('birth_date')
            if birth_date:
                employee.birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
            elif employee.birth_date:  # Clear birth date if field is empty but was previously set
                employee.birth_date = None
            
            db.session.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('employees.view_profile', id=employee.id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error updating employee: {str(e)}', 'danger')
    
    # Get departments and all active employees for form
    departments = Department.query.all()
    managers = Employee.query.filter(
        (Employee.status == 'Active') &
        (Employee.id != id)  # Exclude the current employee
    ).order_by(Employee.last_name, Employee.first_name).all()
    
    return render_template('employees/edit.html', 
                          employee=employee, 
                          departments=departments, 
                          managers=managers,
                          is_new=False,
                          nav_data=nav_data)

@employee_bp.route('/<int:id>/archive', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def archive_employee(id):
    employee = Employee.query.get_or_404(id)
    
    try:
        employee.status = 'Inactive'
        db.session.commit()
        flash('Employee archived successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error archiving employee: {str(e)}', 'danger')
    
    return redirect(url_for('employees.list_employees'))

@employee_bp.route('/create_account/<int:employee_id>', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def create_account(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    
    # Check if employee already has a user account
    if employee.user_id:
        flash('This employee already has a user account.', 'warning')
        return redirect(url_for('employees.view_profile', id=employee_id))
    
    # Generate username from employee's email
    username = employee.email.split('@')[0]
    
    # Check if username already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        # Append a number to make it unique
        count = 1
        while User.query.filter_by(username=f"{username}{count}").first():
            count += 1
        username = f"{username}{count}"
    
    # Get default role (Employee)
    employee_role = Role.query.filter_by(name='Employee').first()
    if not employee_role:
        flash('Employee role not found. Please create roles first.', 'danger')
        return redirect(url_for('employees.view_profile', id=employee_id))
    
    # Generate a default password (employee ID + first 3 letters of last name)
    default_password = f"{employee.employee_id}{employee.last_name[:3].lower()}"
    
    try:
        # Create new user
        new_user = User(
            username=username,
            email=employee.email,
            role_id=employee_role.id
        )
        new_user.set_password(default_password)
        
        db.session.add(new_user)
        db.session.flush()  # Get ID without committing
        
        # Link employee to user
        employee.user_id = new_user.id
        db.session.commit()
        
        flash(f'User account created successfully! Username: {username}, Temporary Password: {default_password}', 'success')
        
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error creating user account: {str(e)}', 'danger')
    
    return redirect(url_for('employees.view_profile', id=employee_id))

@employee_bp.route('/contacts')
@login_required
def contact_list():
    """View company employee contact list."""
    # Base query to get all active employees with their departments
    query = Employee.query.filter_by(status='Active')
    
    # Get filter parameters
    department_id = request.args.get('department', type=int)
    search_term = request.args.get('search')
    
    # Apply filters
    if department_id:
        query = query.filter(Employee.department_id == department_id)
        
    if search_term:
        search = f"%{search_term}%"
        query = query.filter(
            db.or_(
                Employee.first_name.ilike(search),
                Employee.last_name.ilike(search),
                Employee.email.ilike(search),
                Employee.job_title.ilike(search)
            )
        )
    
    # Get all departments for the filter dropdown
    departments = Department.query.order_by(Department.name).all()
    
    # Order by department and then by last name
    employees = query.order_by(Employee.department_id, Employee.last_name).all()
    
    return render_template(
        'employees/contacts.html',
        employees=employees,
        departments=departments,
        filters={
            'department_id': department_id,
            'search_term': search_term
        }
    )

@employee_bp.route('/import', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def import_employees():
    """Bulk import employees from CSV or Excel file."""
    from config import Config
    
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        # Process the uploaded file
        success_count, error_count, errors = process_employee_import(file, Config.UPLOAD_FOLDER)
        
        if success_count > 0:
            flash(f'Successfully imported {success_count} employees. {error_count} errors.', 'success')
        else:
            flash('Import failed. Please check file format and try again.', 'danger')
        
        return render_template(
            'employees/import.html',
            success_count=success_count,
            error_count=error_count,
            errors=errors
        )
    
    return render_template('employees/import.html')

@employee_bp.route('/import-template/<file_format>')
@login_required
@role_required('Admin', 'HR')
def import_template(file_format):
    """Download employee import template."""
    from config import Config
    
    if file_format not in ['csv', 'xlsx']:
        flash('Invalid file format. Choose CSV or Excel.', 'danger')
        return redirect(url_for('employees.import_employees'))
    
    try:
        template_path = get_import_template(Config.UPLOAD_FOLDER, file_format)
        return send_file(
            template_path,
            as_attachment=True,
            download_name=os.path.basename(template_path)
        )
    except Exception as e:
        flash(f'Error generating template: {str(e)}', 'danger')
        return redirect(url_for('employees.import_employees'))
