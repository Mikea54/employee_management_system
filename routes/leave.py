from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from app import db
from models import LeaveRequest, LeaveType, LeaveBalance, Employee
from utils.helpers import role_required, calculate_leave_days

leave_bp = Blueprint('leave', __name__, url_prefix='/leave')

@leave_bp.route('/')
@login_required
def index():
    """Main leave management page."""
    # Different view based on role
    if current_user.role.name in ['Admin', 'HR']:
        return redirect(url_for('leave.manage'))
    elif current_user.role.name == 'Manager':
        return redirect(url_for('leave.pending_approvals'))
    else:
        return redirect(url_for('leave.my_requests'))

@leave_bp.route('/request', methods=['GET', 'POST'])
@login_required
def request_leave():
    """Create new leave request."""
    # Check if user has an employee record
    if not current_user.employee:
        flash('You do not have an employee record.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        try:
            # Extract form data
            leave_type_id = request.form.get('leave_type_id', type=int)
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            reason = request.form.get('reason')
            
            # Validate required fields
            if not leave_type_id or not start_date_str or not end_date_str:
                flash('All fields are required.', 'danger')
                return redirect(url_for('leave.request_leave'))
            
            # Parse dates
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            # Validate date range
            if start_date > end_date:
                flash('End date must be after start date.', 'danger')
                return redirect(url_for('leave.request_leave'))
            
            if start_date < datetime.now().date():
                flash('Start date cannot be in the past.', 'danger')
                return redirect(url_for('leave.request_leave'))
            
            # Calculate days requested
            days_requested = calculate_leave_days(start_date, end_date)
            
            # Check leave balance but allow submission regardless
            leave_balance = LeaveBalance.query.filter_by(
                employee_id=current_user.employee.id,
                leave_type_id=leave_type_id,
                year=datetime.now().year
            ).first()
            
            if not leave_balance:
                flash('Warning: No leave balance found for this leave type. Your request will be submitted but may require HR approval.', 'warning')
            elif days_requested > leave_balance.remaining_days:
                flash(f'Warning: This request exceeds your available balance. You have {leave_balance.remaining_days} days available but are requesting {days_requested} days.', 'warning')
            
            # Create leave request
            leave_request = LeaveRequest(
                employee_id=current_user.employee.id,
                leave_type_id=leave_type_id,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                status='Pending'
            )
            
            db.session.add(leave_request)
            db.session.commit()
            
            flash('Leave request submitted successfully!', 'success')
            return redirect(url_for('leave.my_requests'))
            
        except ValueError as e:
            flash(f'Invalid date format: {str(e)}', 'danger')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'danger')
    
    # Get leave types and balances for form
    leave_types = LeaveType.query.all()
    leave_balances = LeaveBalance.query.filter_by(
        employee_id=current_user.employee.id,
        year=datetime.now().year
    ).all()
    
    return render_template(
        'leave/request.html',
        leave_types=leave_types,
        leave_balances=leave_balances
    )

@leave_bp.route('/my-requests')
@login_required
def my_requests():
    """View employee's own leave requests."""
    # Check if user has an employee record
    if not current_user.employee:
        flash('You do not have an employee record.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Get leave requests
    leave_requests = LeaveRequest.query.filter_by(
        employee_id=current_user.employee.id
    ).order_by(LeaveRequest.created_at.desc()).all()
    
    # Get leave balances
    leave_balances = LeaveBalance.query.filter_by(
        employee_id=current_user.employee.id,
        year=datetime.now().year
    ).all()
    
    return render_template(
        'leave/manage.html',
        leave_requests=leave_requests,
        leave_balances=leave_balances,
        is_personal=True
    )

@leave_bp.route('/cancel/<int:request_id>', methods=['POST'])
@login_required
def cancel_request(request_id):
    """Cancel a pending leave request."""
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Check if this is the employee's own request
    if leave_request.employee_id != current_user.employee.id:
        flash('You can only cancel your own leave requests.', 'danger')
        return redirect(url_for('leave.my_requests'))
    
    # Check if request is still pending
    if leave_request.status != 'Pending':
        flash('Only pending requests can be cancelled.', 'danger')
        return redirect(url_for('leave.my_requests'))
    
    try:
        leave_request.status = 'Cancelled'
        db.session.commit()
        flash('Leave request cancelled successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error cancelling request: {str(e)}', 'danger')
    
    return redirect(url_for('leave.my_requests'))

@leave_bp.route('/pending-approvals')
@login_required
@role_required('Admin', 'HR', 'Manager')
def pending_approvals():
    """View pending leave requests for approval."""
    # Base query
    query = db.session.query(LeaveRequest, Employee, LeaveType).join(
        Employee, LeaveRequest.employee_id == Employee.id
    ).join(
        LeaveType, LeaveRequest.leave_type_id == LeaveType.id
    ).filter(
        LeaveRequest.status == 'Pending'
    )
    
    # Filter based on role
    if current_user.role.name == 'Manager' and current_user.employee:
        # Get all subordinates
        subordinate_ids = [emp.id for emp in current_user.employee.subordinates]
        query = query.filter(Employee.id.in_(subordinate_ids))
    
    # Get results
    pending_requests = query.order_by(LeaveRequest.created_at).all()
    
    # Get leave balances for each employee and leave type
    leave_balances = {}
    current_year = datetime.now().year
    
    # Get all unique employee and leave type combinations
    employee_leave_types = set()
    for _, employee, leave_type in pending_requests:
        employee_leave_types.add((employee.id, leave_type.id))
    
    # Fetch all required balances
    for emp_id, lt_id in employee_leave_types:
        balance = LeaveBalance.query.filter_by(
            employee_id=emp_id,
            leave_type_id=lt_id,
            year=current_year
        ).first()
        
        # Store in dictionary with (employee_id, leave_type_id) as key
        leave_balances[(emp_id, lt_id)] = balance
    
    return render_template(
        'leave/pending_approvals.html',
        pending_requests=pending_requests,
        leave_balances=leave_balances
    )

@leave_bp.route('/approve/<int:request_id>', methods=['POST'])
@login_required
@role_required('Admin', 'HR', 'Manager')
def approve_request(request_id):
    """Approve a leave request."""
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Check permissions
    if current_user.role.name == 'Manager':
        # Check if employee is a subordinate
        if current_user.employee:
            subordinate_ids = [emp.id for emp in current_user.employee.subordinates]
            if leave_request.employee_id not in subordinate_ids:
                flash('You can only approve leave for your subordinates.', 'danger')
                return redirect(url_for('leave.pending_approvals'))
        else:
            flash('Manager account not linked to an employee record.', 'danger')
            return redirect(url_for('leave.pending_approvals'))
    
    try:
        # Approve the request
        leave_request.status = 'Approved'
        leave_request.approved_by = current_user.id
        leave_request.approval_date = datetime.now()
        
        # Update leave balance
        days_taken = calculate_leave_days(leave_request.start_date, leave_request.end_date)
        
        leave_balance = LeaveBalance.query.filter_by(
            employee_id=leave_request.employee_id,
            leave_type_id=leave_request.leave_type_id,
            year=datetime.now().year
        ).first()
        
        # Convert days to hours (8 hours per day)
        hours_taken = days_taken * 8
        
        if leave_balance:
            leave_balance.used_hours += hours_taken
        else:
            # Create a balance record if one doesn't exist
            new_balance = LeaveBalance(
                employee_id=leave_request.employee_id,
                leave_type_id=leave_request.leave_type_id,
                year=datetime.now().year,
                total_hours=hours_taken,  # Start with minimum balance equal to the request
                used_hours=hours_taken,
                accrual_rate=2.80  # Default accrual rate
            )
            db.session.add(new_balance)
            flash('Created new leave balance record for this employee.', 'info')
        
        db.session.commit()
        flash('Leave request approved successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error approving request: {str(e)}', 'danger')
    
    return redirect(url_for('leave.pending_approvals'))

@leave_bp.route('/reject/<int:request_id>', methods=['POST'])
@login_required
@role_required('Admin', 'HR', 'Manager')
def reject_request(request_id):
    """Reject a leave request."""
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Check permissions similar to approve
    if current_user.role.name == 'Manager':
        if current_user.employee:
            subordinate_ids = [emp.id for emp in current_user.employee.subordinates]
            if leave_request.employee_id not in subordinate_ids:
                flash('You can only manage leave for your subordinates.', 'danger')
                return redirect(url_for('leave.pending_approvals'))
        else:
            flash('Manager account not linked to an employee record.', 'danger')
            return redirect(url_for('leave.pending_approvals'))
    
    try:
        # Reject the request
        leave_request.status = 'Rejected'
        leave_request.approved_by = current_user.id
        leave_request.approval_date = datetime.now()
        
        db.session.commit()
        flash('Leave request rejected.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error rejecting request: {str(e)}', 'danger')
    
    return redirect(url_for('leave.pending_approvals'))

@leave_bp.route('/manage')
@login_required
@role_required('Admin', 'HR')
def manage():
    """Manage all leave requests (Admin/HR only)."""
    # Get filter parameters
    employee_id = request.args.get('employee_id', type=int)
    leave_type_id = request.args.get('leave_type_id', type=int)
    status = request.args.get('status')
    
    # Base query
    query = db.session.query(LeaveRequest, Employee, LeaveType).join(
        Employee, LeaveRequest.employee_id == Employee.id
    ).join(
        LeaveType, LeaveRequest.leave_type_id == LeaveType.id
    )
    
    # Apply filters
    if employee_id:
        query = query.filter(Employee.id == employee_id)
    
    if leave_type_id:
        query = query.filter(LeaveRequest.leave_type_id == leave_type_id)
    
    if status:
        query = query.filter(LeaveRequest.status == status)
    
    # Get results
    leave_requests = query.order_by(LeaveRequest.created_at.desc()).all()
    
    # Get filter options
    employees = Employee.query.filter_by(status='Active').all()
    leave_types = LeaveType.query.all()
    
    return render_template(
        'leave/manage.html',
        leave_requests=leave_requests,
        employees=employees,
        leave_types=leave_types,
        current_filters={
            'employee_id': employee_id,
            'leave_type_id': leave_type_id,
            'status': status
        },
        is_personal=False
    )

@leave_bp.route('/leave-types')
@login_required
@role_required('Admin', 'HR')
def leave_types():
    """Manage leave types and balances in a combined view."""
    # Get all leave types
    leave_types = LeaveType.query.all()
    
    # Get current year
    year = request.args.get('year', default=datetime.now().year, type=int)
    
    # Get all employees
    employees = Employee.query.filter_by(status='Active').order_by(Employee.last_name).all()
    
    # Get years for filter (starting from hire date of earliest employee to next year)
    earliest_hire = db.session.query(db.func.min(Employee.hire_date)).scalar()
    if earliest_hire:
        start_year = earliest_hire.year
    else:
        start_year = datetime.now().year
    
    years = list(range(start_year, datetime.now().year + 2))
    
    # Get existing balances for the selected year
    balances_query = db.session.query(
        LeaveBalance, Employee, LeaveType
    ).join(
        Employee, LeaveBalance.employee_id == Employee.id
    ).join(
        LeaveType, LeaveBalance.leave_type_id == LeaveType.id
    ).filter(
        LeaveBalance.year == year
    ).order_by(Employee.last_name, Employee.first_name).all()
    
    return render_template(
        'leave/types_and_balances.html', 
        leave_types=leave_types,
        employees=employees,
        balances=balances_query,
        years=years,
        current_year=year
    )

@leave_bp.route('/leave-types/add', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def add_leave_type():
    """Add a new leave type."""
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        is_paid = bool(int(request.form.get('is_paid', 1)))
        
        # Validate input
        if not name or not description:
            flash('Name and description are required.', 'danger')
            return redirect(url_for('leave.leave_types'))
        
        # Check if name already exists
        existing = LeaveType.query.filter_by(name=name).first()
        if existing:
            flash(f'A leave type with the name "{name}" already exists.', 'danger')
            return redirect(url_for('leave.leave_types'))
        
        # Create new leave type
        leave_type = LeaveType(
            name=name,
            description=description,
            is_paid=is_paid
        )
        
        db.session.add(leave_type)
        db.session.commit()
        
        flash(f'Leave type "{name}" added successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error adding leave type: {str(e)}', 'danger')
    
    return redirect(url_for('leave.leave_types'))

@leave_bp.route('/leave-types/edit', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def edit_leave_type():
    """Edit an existing leave type."""
    try:
        leave_type_id = request.form.get('leave_type_id', type=int)
        name = request.form.get('name')
        description = request.form.get('description')
        is_paid = bool(int(request.form.get('is_paid', 1)))
        
        # Validate input
        if not leave_type_id or not name or not description:
            flash('All fields are required.', 'danger')
            return redirect(url_for('leave.leave_types'))
        
        # Get leave type
        leave_type = LeaveType.query.get_or_404(leave_type_id)
        
        # Check for name conflict if name is changed
        if leave_type.name != name:
            existing = LeaveType.query.filter_by(name=name).first()
            if existing:
                flash(f'A leave type with the name "{name}" already exists.', 'danger')
                return redirect(url_for('leave.leave_types'))
        
        # Update leave type
        leave_type.name = name
        leave_type.description = description
        leave_type.is_paid = is_paid
        
        db.session.commit()
        
        flash(f'Leave type "{name}" updated successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error updating leave type: {str(e)}', 'danger')
    
    return redirect(url_for('leave.leave_types'))

@leave_bp.route('/leave-types/delete', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def delete_leave_type():
    """Delete a leave type."""
    try:
        leave_type_id = request.form.get('leave_type_id', type=int)
        
        if not leave_type_id:
            flash('Invalid leave type ID.', 'danger')
            return redirect(url_for('leave.leave_types'))
        
        # Get leave type
        leave_type = LeaveType.query.get_or_404(leave_type_id)
        
        # Check if in use
        if leave_type.leave_requests.count() > 0:
            flash(f'Cannot delete leave type "{leave_type.name}" because it has associated leave requests.', 'danger')
            return redirect(url_for('leave.leave_types'))
        
        # Delete leave balances associated with this type
        LeaveBalance.query.filter_by(leave_type_id=leave_type_id).delete()
        
        # Delete the leave type
        db.session.delete(leave_type)
        db.session.commit()
        
        flash(f'Leave type "{leave_type.name}" deleted successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error deleting leave type: {str(e)}', 'danger')
    
    return redirect(url_for('leave.leave_types'))

@leave_bp.route('/all-balances')
@login_required
@role_required('Admin', 'HR')
def all_balances():
    """Admin screen to view all leave balances at a glance."""
    # Get query parameters
    year = request.args.get('year', default=datetime.now().year, type=int)
    
    # Get years for filter
    earliest_hire = db.session.query(db.func.min(Employee.hire_date)).scalar()
    if earliest_hire:
        start_year = earliest_hire.year
    else:
        start_year = datetime.now().year
    
    years = list(range(start_year, datetime.now().year + 2))
    
    # Get all employees
    employees = Employee.query.filter_by(status='Active').order_by(Employee.last_name).all()
    
    # Get all leave types
    leave_types = LeaveType.query.all()
    
    # Get all balances for the selected year
    all_balances = LeaveBalance.query.filter_by(year=year).all()
    
    # Organize balances by employee and leave type for easy table rendering
    balances_by_employee = {}
    for balance in all_balances:
        if balance.employee_id not in balances_by_employee:
            balances_by_employee[balance.employee_id] = {}
        balances_by_employee[balance.employee_id][balance.leave_type_id] = balance
    
    return render_template(
        'leave/all_balances.html',
        employees=employees,
        leave_types=leave_types,
        balances=balances_by_employee,
        years=years,
        current_year=year
    )

@leave_bp.route('/balances')
@login_required
@role_required('Admin', 'HR')
def manage_balances():
    """View and manage leave balances for all employees."""
    # Get query parameters
    employee_id = request.args.get('employee_id', type=int)
    leave_type_id = request.args.get('leave_type_id', type=int)
    year = request.args.get('year', default=datetime.now().year, type=int)
    
    # Base query
    query = db.session.query(
        LeaveBalance, Employee, LeaveType
    ).join(
        Employee, LeaveBalance.employee_id == Employee.id
    ).join(
        LeaveType, LeaveBalance.leave_type_id == LeaveType.id
    ).filter(
        LeaveBalance.year == year
    )
    
    # Apply filters
    if employee_id:
        query = query.filter(Employee.id == employee_id)
    
    if leave_type_id:
        query = query.filter(LeaveBalance.leave_type_id == leave_type_id)
    
    # Get results
    balances = query.order_by(Employee.last_name, Employee.first_name).all()
    
    # Get filter options - create a list of objects with consistent attributes for template
    employees_query = Employee.query.filter_by(status='Active').order_by(Employee.last_name).all()
    employees = []
    for emp in employees_query:
        employees.append({
            'id': emp.id,
            'name': f"{emp.first_name} {emp.last_name}",
            'department': emp.department
        })
    
    leave_types = LeaveType.query.all()
    
    # Get years for filter (starting from hire date of earliest employee to next year)
    earliest_hire = db.session.query(db.func.min(Employee.hire_date)).scalar()
    if earliest_hire:
        start_year = earliest_hire.year
    else:
        start_year = datetime.now().year
    
    years = list(range(start_year, datetime.now().year + 2))
    
    return render_template(
        'leave/balances.html',
        balances=balances,
        employees=employees,
        leave_types=leave_types,
        years=years,
        current_filters={
            'employee_id': employee_id,
            'leave_type_id': leave_type_id,
            'year': year
        }
    )

@leave_bp.route('/balances/create', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def create_balance():
    """Create or update a leave balance."""
    try:
        employee_id = request.form.get('employee_id', type=int)
        leave_type_id = request.form.get('leave_type_id', type=int)
        year = request.form.get('year', type=int)
        total_hours = request.form.get('total_hours', type=float)
        used_hours = request.form.get('used_hours', 0, type=float)
        accrual_rate = request.form.get('accrual_rate', 2.80, type=float)
        
        # Validate input
        if not employee_id or not leave_type_id or not year or total_hours is None:
            flash('All fields are required.', 'danger')
            return redirect(url_for('leave.manage_balances'))
        
        # Check if balance already exists
        existing = LeaveBalance.query.filter_by(
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            year=year
        ).first()
        
        if existing:
            # Update existing balance
            existing.total_hours = total_hours
            existing.used_hours = used_hours
            existing.accrual_rate = accrual_rate
            db.session.commit()
            flash('Leave balance updated successfully.', 'success')
        else:
            # Create new balance
            balance = LeaveBalance(
                employee_id=employee_id,
                leave_type_id=leave_type_id,
                year=year,
                total_hours=total_hours,
                used_hours=used_hours,
                accrual_rate=accrual_rate
            )
            db.session.add(balance)
            db.session.commit()
            flash('Leave balance created successfully.', 'success')
    
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error managing leave balance: {str(e)}', 'danger')
    
    return redirect(url_for('leave.manage_balances'))

@leave_bp.route('/balances/initialize', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def initialize_balances():
    """Initialize leave balances for all employees."""
    try:
        year = request.form.get('year', default=datetime.now().year, type=int)
        default_hours = request.form.get('default_hours', default=160, type=float)  # 20 days * 8 hours
        default_accrual_rate = request.form.get('accrual_rate', default=2.80, type=float)
        
        # Get all active employees
        employees = Employee.query.filter_by(status='Active').all()
        
        # Get all leave types
        leave_types = LeaveType.query.all()
        
        # Count of balances created
        created_count = 0
        
        # For each employee and leave type, create a balance if one doesn't exist
        for employee in employees:
            for leave_type in leave_types:
                # Check if balance already exists
                existing = LeaveBalance.query.filter_by(
                    employee_id=employee.id,
                    leave_type_id=leave_type.id,
                    year=year
                ).first()
                
                if not existing:
                    # Create new balance with default hours
                    balance = LeaveBalance(
                        employee_id=employee.id,
                        leave_type_id=leave_type.id,
                        year=year,
                        total_hours=default_hours,
                        used_hours=0,
                        accrual_rate=default_accrual_rate
                    )
                    db.session.add(balance)
                    created_count += 1
        
        db.session.commit()
        
        if created_count > 0:
            flash(f'Successfully initialized {created_count} leave balances for {year}.', 'success')
        else:
            flash(f'No new leave balances needed to be created for {year}.', 'info')
    
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error initializing leave balances: {str(e)}', 'danger')
    
    return redirect(url_for('leave.manage_balances'))
