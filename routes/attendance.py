from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from app import db
from models import Attendance, Employee, Department
from utils.helpers import role_required

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

@attendance_bp.route('/')
@login_required
def index():
    return render_template('attendance/track.html')

@attendance_bp.route('/status')
@login_required
def attendance_status():
    # Check if user has an employee record
    if not current_user.employee:
        return jsonify({
            "clocked_in": False,
            "clocked_out": False,
            "message": "No employee record found"
        })
    
    # Get today's attendance records, ordered by creation time (latest first)
    today = datetime.now().date()
    records = Attendance.query.filter_by(
        employee_id=current_user.employee.id,
        date=today
    ).order_by(Attendance.id.desc()).all()
    
    if records:
        latest_record = records[0]  # Get the most recent attendance record
        
        # Check if the latest record has a clock-out time
        # If it does, the user can clock in again for a new session
        if latest_record.clock_in and latest_record.clock_out:
            return jsonify({
                "clocked_in": False,
                "clocked_out": True,
                "clock_in": latest_record.clock_in.isoformat(),
                "clock_out": latest_record.clock_out.isoformat(),
                "status": latest_record.status,
                "multiple_sessions": len(records) > 1,
                "can_clock_in_again": True
            })
        elif latest_record.clock_in and not latest_record.clock_out:
            # User is currently clocked in
            return jsonify({
                "clocked_in": True,
                "clocked_out": False,
                "clock_in": latest_record.clock_in.isoformat(),
                "clock_out": None,
                "status": latest_record.status,
                "multiple_sessions": len(records) > 1,
                "can_clock_in_again": False
            })
        else:
            # No clock in/out recorded yet
            return jsonify({
                "clocked_in": False,
                "clocked_out": False,
                "status": latest_record.status if hasattr(latest_record, 'status') else "Unknown",
                "multiple_sessions": len(records) > 1,
                "can_clock_in_again": True
            })
    else:
        return jsonify({
            "clocked_in": False,
            "clocked_out": False,
            "message": "No attendance record for today",
            "can_clock_in_again": True
        })

@attendance_bp.route('/clock_in', methods=['POST'])
@login_required
def clock_in():
    # Check if user has an employee record
    if not current_user.employee:
        flash('You do not have an employee record.', 'danger')
        return redirect(url_for('attendance.index'))
    
    today = datetime.now().date()
    now = datetime.now()
    
    # Check if already clocked in today
    existing_record = Attendance.query.filter_by(
        employee_id=current_user.employee.id,
        date=today
    ).order_by(Attendance.id.desc()).first()
    
    try:
        # Create or update attendance record
        if existing_record:
            # If the user has clocked in and out completely, create a new entry for the new session
            if existing_record.clock_in and existing_record.clock_out:
                new_record = Attendance(
                    employee_id=current_user.employee.id,
                    date=today,
                    clock_in=now,
                    status='Present',
                    notes=f"Multiple sessions: Clocked in again at {now.strftime('%H:%M:%S')}"
                )
                db.session.add(new_record)
                flash('Started new attendance session for today!', 'success')
            # If already clocked in but not out, show a warning
            elif existing_record.clock_in and not existing_record.clock_out:
                flash('You are already clocked in. Please clock out before starting a new session.', 'warning')
                return redirect(url_for('attendance.index'))
            # Normal scenario, set clock in time
            else:
                existing_record.clock_in = now
                existing_record.status = 'Present'
                flash('Clock-in successful!', 'success')
        else:
            new_record = Attendance(
                employee_id=current_user.employee.id,
                date=today,
                clock_in=now,
                status='Present'
            )
            db.session.add(new_record)
            flash('Clock-in successful!', 'success')
        
        db.session.commit()
        
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error recording attendance: {str(e)}', 'danger')
    
    return redirect(url_for('attendance.index'))

@attendance_bp.route('/clock_out', methods=['POST'])
@login_required
def clock_out():
    # Check if user has an employee record
    if not current_user.employee:
        flash('You do not have an employee record.', 'danger')
        return redirect(url_for('attendance.index'))
    
    today = datetime.now().date()
    
    # Find today's attendance record
    record = Attendance.query.filter_by(
        employee_id=current_user.employee.id,
        date=today
    ).first()
    
    if not record or not record.clock_in:
        flash('You need to clock in first.', 'warning')
        return redirect(url_for('attendance.index'))
    
    if record.clock_out:
        flash('You have already clocked out today.', 'warning')
        return redirect(url_for('attendance.index'))
    
    try:
        # Update record with clock-out time
        record.clock_out = datetime.now()
        db.session.commit()
        flash('Clock-out successful!', 'success')
        
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error recording attendance: {str(e)}', 'danger')
    
    return redirect(url_for('attendance.index'))

@attendance_bp.route('/my_attendance')
@login_required
def my_attendance():
    # Check if user has an employee record
    if not current_user.employee:
        flash('You do not have an employee record.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Get date range from query parameters or default to current month
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            start_date, end_date = get_default_date_range()
    else:
        start_date, end_date = get_default_date_range()
    
    # Get attendance records for the date range
    attendance_records = Attendance.query.filter(
        Attendance.employee_id == current_user.employee.id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).order_by(Attendance.date.desc()).all()
    
    # Calculate working days
    business_days = sum(1 for d in range((end_date - start_date).days + 1)
                        if (start_date + timedelta(days=d)).weekday() < 5)
    
    # Calculate attendance stats
    present_days = sum(1 for record in attendance_records if record.status == 'Present')
    
    return render_template(
        'attendance/reports.html',
        attendance_records=attendance_records,
        start_date=start_date,
        end_date=end_date,
        employee=current_user.employee,
        is_personal=True,
        business_days=business_days,
        present_days=present_days
    )

@attendance_bp.route('/reports')
@login_required
@role_required('Admin', 'HR', 'Manager')
def reports():
    # Get filter parameters
    employee_id = request.args.get('employee_id', type=int)
    department_id = request.args.get('department_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    status = request.args.get('status')
    
    # Process date range
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            start_date, end_date = get_default_date_range()
    else:
        start_date, end_date = get_default_date_range()
    
    # Base query
    query = db.session.query(Attendance, Employee).join(
        Employee, Attendance.employee_id == Employee.id
    ).filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )
    
    # Apply filters
    if employee_id:
        query = query.filter(Employee.id == employee_id)
    
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    
    if status:
        query = query.filter(Attendance.status == status)
    
    # Apply manager filter for Manager role
    if current_user.role.name == 'Manager' and current_user.employee:
        # Get all subordinates
        subordinate_ids = [emp.id for emp in current_user.employee.subordinates]
        query = query.filter(Employee.id.in_(subordinate_ids))
    
    # Execute query
    results = query.order_by(Attendance.date.desc(), Employee.last_name).all()
    
    # Get all employees and departments for filters
    if current_user.role.name in ['Admin', 'HR']:
        employees = Employee.query.filter_by(status='Active').all()
    elif current_user.role.name == 'Manager' and current_user.employee:
        subordinate_ids = [emp.id for emp in current_user.employee.subordinates]
        employees = Employee.query.filter(Employee.id.in_(subordinate_ids)).all()
    else:
        employees = []
    
    departments = Department.query.all()
    
    # Calculate working days
    business_days = sum(1 for d in range((end_date - start_date).days + 1)
                       if (start_date + timedelta(days=d)).weekday() < 5)
    
    return render_template(
        'attendance/reports.html',
        results=results,
        start_date=start_date,
        end_date=end_date,
        employees=employees,
        departments=departments,
        current_filters={
            'employee_id': employee_id,
            'department_id': department_id,
            'status': status
        },
        is_personal=False,
        business_days=business_days
    )

@attendance_bp.route('/manage', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR', 'Manager')
def manage_attendance():
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', type=int)
        date_str = request.form.get('date')
        status = request.form.get('status')
        clock_in_str = request.form.get('clock_in')
        clock_out_str = request.form.get('clock_out')
        notes = request.form.get('notes')
        
        try:
            # Validate data
            if not employee_id or not date_str or not status:
                raise ValueError("Employee, date, and status are required.")
            
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Process clock times if provided
            clock_in = None
            if clock_in_str:
                clock_in = datetime.combine(
                    date, 
                    datetime.strptime(clock_in_str, '%H:%M').time()
                )
            
            clock_out = None
            if clock_out_str:
                clock_out = datetime.combine(
                    date, 
                    datetime.strptime(clock_out_str, '%H:%M').time()
                )
            
            # Check if record already exists
            attendance = Attendance.query.filter_by(
                employee_id=employee_id,
                date=date
            ).first()
            
            if attendance:
                # Update existing record
                attendance.status = status
                attendance.clock_in = clock_in
                attendance.clock_out = clock_out
                attendance.notes = notes
            else:
                # Create new record
                attendance = Attendance(
                    employee_id=employee_id,
                    date=date,
                    status=status,
                    clock_in=clock_in,
                    clock_out=clock_out,
                    notes=notes
                )
                db.session.add(attendance)
            
            db.session.commit()
            flash('Attendance record saved successfully.', 'success')
            
        except ValueError as e:
            flash(f'Error: {str(e)}', 'danger')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'danger')
    
    # Get employees based on role
    if current_user.role.name in ['Admin', 'HR']:
        employees = Employee.query.filter_by(status='Active').all()
    elif current_user.role.name == 'Manager' and current_user.employee:
        subordinate_ids = [emp.id for emp in current_user.employee.subordinates]
        employees = Employee.query.filter(
            Employee.id.in_(subordinate_ids),
            Employee.status == 'Active'
        ).all()
    else:
        employees = []
    
    return render_template('attendance/manage.html', employees=employees, now=datetime.now())

def get_default_date_range():
    """Return default date range (current month)"""
    today = datetime.now().date()
    start_date = today.replace(day=1)
    
    # Calculate end of month
    if today.month == 12:
        end_date = today.replace(day=31)
    else:
        next_month = today.replace(month=today.month+1, day=1)
        end_date = next_month - timedelta(days=1)
    
    return start_date, end_date
