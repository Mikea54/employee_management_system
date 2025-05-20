import secrets

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from app import db
from models import User, Role, Permission, Department, Employee, PayPeriod
from utils.helpers import role_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def settings():
    """System settings page."""
    if request.method == 'POST':
        # Process form data
        try:
            # Company Information
            company_name = request.form.get('company_name')
            
            # Email Settings
            email_from = request.form.get('email_from')
            enable_emails = 'enable_emails' in request.form
            
            # System Configuration
            time_zone = request.form.get('time_zone')
            date_format = request.form.get('date_format')
            
            # In a real application, you would save these settings to a database
            # or configuration file. For now, we'll just flash a success message.
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('admin.settings'))
        except Exception as e:
            flash(f'Error updating settings: {str(e)}', 'danger')
    
    return render_template('admin/settings.html')

@admin_bp.route('/users')
@login_required
@role_required('Admin')
def user_management():
    """User management page."""
    users = User.query.all()
    roles = Role.query.all()
    all_permissions = Permission.query.all()
    return render_template('admin/users.html', users=users, roles=roles, all_permissions=all_permissions)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def edit_user(user_id):
    """Edit user details."""
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role_id = request.form.get('role_id')
        is_active = 'is_active' in request.form
        
        # Validate data
        if not username or not email or not role_id:
            flash('All fields are required.', 'danger')
            return render_template('admin/edit_user.html', user=user, roles=roles)
        
        # Check if username already exists for another user
        existing_user = User.query.filter(User.username == username, User.id != user_id).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return render_template('admin/edit_user.html', user=user, roles=roles)
        
        # Check if email already exists for another user
        existing_email = User.query.filter(User.email == email, User.id != user_id).first()
        if existing_email:
            flash('Email already exists.', 'danger')
            return render_template('admin/edit_user.html', user=user, roles=roles)
        
        # Update user
        user.username = username
        user.email = email
        user.role_id = role_id
        user.is_active = is_active
        
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.user_management'))
    
    return render_template('admin/edit_user.html', user=user, roles=roles)

@admin_bp.route('/users/reset-password/<int:user_id>', methods=['POST'])
@login_required
@role_required('Admin')
def reset_password(user_id):
    """Reset user password to a secure random value."""
    user = User.query.get_or_404(user_id)

    # Generate a secure random password and set it
    new_password = secrets.token_urlsafe(8)
    user.set_password(new_password)

    db.session.commit()
    flash(
        f'Password reset successfully for {user.username}. New password: '
        f'{new_password}',
        'success'
    )
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/roles/create', methods=['POST'])
@login_required
@role_required('Admin')
def create_role():
    """Create a new role with permissions."""
    name = request.form.get('name')
    description = request.form.get('description')
    permissions = request.form.getlist('permissions[]')
    
    # Validate data
    if not name:
        flash('Role name is required.', 'danger')
        return redirect(url_for('admin.user_management'))
    
    # Check if name already exists
    existing_role = Role.query.filter_by(name=name).first()
    if existing_role:
        flash('Role name already exists.', 'danger')
        return redirect(url_for('admin.user_management'))
    
    # Create role
    new_role = Role()
    new_role.name = name
    new_role.description = description

    # Attach permissions
    for perm_name in permissions:
        perm = Permission.query.filter_by(name=perm_name).first()
        if perm:
            new_role.permissions.append(perm)
    
    db.session.add(new_role)
    db.session.commit()
    
    flash('Role created successfully.', 'success')
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/roles/edit/<int:role_id>', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def edit_role(role_id):
    """Edit role details."""
    role = Role.query.get_or_404(role_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        permissions = request.form.getlist('permissions[]')
        
        # Validate data
        if not name:
            flash('Role name is required.', 'danger')
            all_permissions = Permission.query.all()
            return render_template('admin/edit_role.html', role=role, permissions=permissions, all_permissions=all_permissions)
        
        # Check if name already exists for another role
        existing_role = Role.query.filter(Role.name == name, Role.id != role_id).first()
        if existing_role:
            flash('Role name already exists.', 'danger')
            all_permissions = Permission.query.all()
            return render_template('admin/edit_role.html', role=role, permissions=permissions, all_permissions=all_permissions)
        
        # Update role
        role.name = name
        role.description = description

        # Update permissions
        role.permissions.clear()
        for perm_name in permissions:
            perm = Permission.query.filter_by(name=perm_name).first()
            if perm:
                role.permissions.append(perm)
        
        db.session.commit()
        flash('Role updated successfully.', 'success')
        return redirect(url_for('admin.user_management'))
    
    # Get current permission names
    permissions = [p.name for p in role.permissions]
    all_permissions = Permission.query.all()
    return render_template('admin/edit_role.html', role=role, permissions=permissions, all_permissions=all_permissions)

@admin_bp.route('/departments', methods=['GET'])
@login_required
@role_required('Admin', 'HR')
def department_settings():
    """Department management page"""
    departments = Department.query.all()
    return render_template('admin/departments.html', departments=departments)

@admin_bp.route('/departments/add', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def add_department():
    """Add a new department"""
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    if not name:
        flash('Department name is required.', 'danger')
        return redirect(url_for('admin.department_settings'))
    
    # Check if department already exists
    existing_dept = Department.query.filter_by(name=name).first()
    if existing_dept:
        flash(f'Department "{name}" already exists.', 'danger')
        return redirect(url_for('admin.department_settings'))
    
    try:
        # Create new department
        new_dept = Department()
        new_dept.name = name
        new_dept.description = description
        
        db.session.add(new_dept)
        db.session.commit()
        flash(f'Department "{name}" created successfully!', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error creating department: {str(e)}', 'danger')
    
    return redirect(url_for('admin.department_settings'))

@admin_bp.route('/departments/edit/<int:dept_id>', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def edit_department(dept_id):
    """Edit department details"""
    department = Department.query.get_or_404(dept_id)
    
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    if not name:
        flash('Department name is required.', 'danger')
        return redirect(url_for('admin.department_settings'))
    
    # Check if name already exists for another department
    existing_dept = Department.query.filter(Department.name == name, Department.id != dept_id).first()
    if existing_dept:
        flash(f'Department "{name}" already exists.', 'danger')
        return redirect(url_for('admin.department_settings'))
    
    try:
        department.name = name
        department.description = description
        
        db.session.commit()
        flash(f'Department "{name}" updated successfully!', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error updating department: {str(e)}', 'danger')
    
    return redirect(url_for('admin.department_settings'))

@admin_bp.route('/departments/delete/<int:dept_id>', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def delete_department(dept_id):
    """Delete a department"""
    department = Department.query.get_or_404(dept_id)
    
    # Check if department has employees
    if department.employees.count() > 0:
        flash('Cannot delete department that has employees assigned to it.', 'danger')
        return redirect(url_for('admin.department_settings'))
    
    try:
        db.session.delete(department)
        db.session.commit()
        flash(f'Department "{department.name}" deleted successfully!', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error deleting department: {str(e)}', 'danger')
    
    return redirect(url_for('admin.department_settings'))

@admin_bp.route('/bulk-updates', methods=['GET'])
@login_required
@role_required('Admin', 'HR')
def bulk_updates():
    """Bulk updates form for employee departments and managers via file upload"""
    departments = Department.query.all()
    return render_template('admin/bulk_updates.html', departments=departments)

@admin_bp.route('/bulk-updates/process', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def process_bulk_updates():
    """Process bulk updates for employees via CSV/Excel upload"""
    if 'upload_file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('admin.bulk_updates'))
    
    uploaded_file = request.files['upload_file']
    if uploaded_file.filename is None or uploaded_file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('admin.bulk_updates'))
    
    # Check file extension
    filename = uploaded_file.filename
    if '.' not in filename:
        flash('Invalid file format. Please upload a CSV or Excel file.', 'danger')
        return redirect(url_for('admin.bulk_updates'))
    
    file_ext = filename.rsplit('.', 1)[1].lower()
    if file_ext not in ['csv', 'xlsx', 'xls']:
        flash('Invalid file format. Please upload a CSV or Excel file.', 'danger')
        return redirect(url_for('admin.bulk_updates'))
    
    try:
        # Process the uploaded file for bulk updates
        from utils.importers import process_employee_bulk_update
        result = process_employee_bulk_update(uploaded_file)
        
        if result['success']:
            flash(f"Successfully processed {result['updated']} employee updates. {result['errors']} errors found.", 
                 'success' if result['errors'] == 0 else 'warning')
        else:
            flash(f"Error processing bulk update: {result['message']}", 'danger')
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'danger')
    
    return redirect(url_for('admin.bulk_updates'))

@admin_bp.route('/bulk-updates/template', methods=['GET'])
@login_required
@role_required('Admin', 'HR')
def bulk_update_template():
    """Download template for bulk updates"""
    import pandas as pd
    from io import BytesIO
    
    file_format = request.args.get('format', 'xlsx')
    
    # Create a template DataFrame
    columns = ['employee_id', 'department_id', 'department_name', 'manager_id', 'manager_employee_id', 'is_manager']
    df = pd.DataFrame(columns=columns)
    
    # Add example row
    df.loc[0] = ['EMP123', 1, 'HR', 2, 'EMP456', 'Yes']
    
    # Add descriptions/instructions
    descriptions = pd.DataFrame({
        'employee_id': ['Employee ID (required)'],
        'department_id': ['Department ID (use either ID or name)'],
        'department_name': ['Department Name (use either ID or name)'],
        'manager_id': ['Manager ID (optional)'],
        'manager_employee_id': ['Manager Employee ID (optional)'],
        'is_manager': ['Set as manager: Yes/No (optional)']
    })
    
    # Create output buffer
    output = BytesIO()
    
    # Write to buffer
    if file_format == 'csv':
        # CSV format
        df.to_csv(output, index=False)
        mimetype = 'text/csv'
        filename = 'bulk_update_template.csv'
    else:
        # Excel format with multiple sheets
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Template', index=False)
            descriptions.to_excel(writer, sheet_name='Instructions', index=False)
            
            # Add department reference sheet
            departments = Department.query.all()
            dept_data = [{'id': dept.id, 'name': dept.name} for dept in departments]
            if dept_data:
                pd.DataFrame(dept_data).to_excel(writer, sheet_name='Departments', index=False)
                
            # Add manager reference sheet using is_manager flag
            managers = Employee.query.filter_by(is_manager=True).all()
            manager_data = [{
                'id': mgr.id, 
                'employee_id': mgr.employee_id,
                'name': mgr.full_name,
                'job_title': mgr.job_title
            } for mgr in managers]
            if manager_data:
                pd.DataFrame(manager_data).to_excel(writer, sheet_name='Managers', index=False)
        
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = 'bulk_update_template.xlsx'
    
    # Rewind buffer
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )


@admin_bp.route('/pay-periods')
@login_required
@role_required('Admin', 'HR')
def manage_pay_periods():
    """View all pay periods"""
    pay_periods = PayPeriod.query.order_by(PayPeriod.start_date.desc()).all()
    return render_template(
        'admin/pay_periods.html',
        pay_periods=pay_periods
    )