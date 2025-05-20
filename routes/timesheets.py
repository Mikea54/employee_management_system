from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from models import Employee, PayPeriod, Timesheet, TimeEntry, Attendance
from create_pay_periods import create_initial_pay_periods
from utils.helpers import role_required
from datetime import datetime, timedelta, date
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_, or_
import calendar

timesheet_bp = Blueprint('timesheets', __name__)

# Helper functions
def get_current_pay_period():
    """Get the current pay period or create one if it doesn't exist"""
    today = datetime.now().date()
    current_period = PayPeriod.query.filter(
        PayPeriod.start_date <= today,
        PayPeriod.end_date >= today
    ).first()
    
    if current_period:
        return current_period
    
    # If no current period exists, create one
    # Start date is the most recent Monday before today, or today if it's Monday
    days_since_monday = today.weekday()
    start_date = today - timedelta(days=days_since_monday)
    
    # End date is 13 days after start (for a two-week period)
    end_date = start_date + timedelta(days=13)
    
    new_period = PayPeriod(
        start_date=start_date,
        end_date=end_date,
        status='Open'
    )
    db.session.add(new_period)
    db.session.commit()
    return new_period

def calculate_hours_from_attendance(employee_id, date_obj):
    """Calculate hours worked on a specific date from attendance records
    
    This function calculates hours for both past and future dates where attendance
    records exist, regardless of the current date.
    """
    # Get attendance record for this date
    attendance = Attendance.query.filter_by(
        employee_id=employee_id,
        date=date_obj
    ).first()
    
    # If there's no attendance record, or missing clock in/out, return 0
    if not attendance:
        return 0.0
    
    # For future dates, still use attendance if it exists
    if attendance.clock_in and attendance.clock_out:
        # Calculate time difference in hours
        clock_in_time = attendance.clock_in
        clock_out_time = attendance.clock_out
        
        # Calculate difference in seconds and convert to hours
        time_diff = (clock_out_time - clock_in_time).total_seconds() / 3600
        # Round to nearest 0.5 hours (30 minutes)
        return round(time_diff * 2) / 2
    
    # If there's a status of "Present" but no clock times, use a default of 8 hours
    if attendance.status == "Present":
        return 8.0
    
    return 0.0

def get_employee_timesheet(employee_id, pay_period_id):
    """Get an employee's timesheet for a specific pay period or create one"""
    timesheet = Timesheet.query.filter_by(
        employee_id=employee_id,
        pay_period_id=pay_period_id
    ).first()
    
    if not timesheet:
        timesheet = Timesheet(
            employee_id=employee_id,
            pay_period_id=pay_period_id,
            status='Draft'
        )
        db.session.add(timesheet)
        db.session.commit()
    
    return timesheet

# Routes
@timesheet_bp.route('/instructions')
@login_required
def instructions():
    """Timesheet instructions page"""
    return render_template('timesheets/instructions.html')

@timesheet_bp.route('/my-timesheet')
@login_required
def my_timesheet():
    """Direct access to current employee's timesheet"""
    employee = current_user.employee
    if not employee:
        flash('No employee profile associated with this account.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    # Get current pay period
    current_period = get_current_pay_period()
    
    # Get employee's timesheet or create it if it doesn't exist
    timesheet = get_employee_timesheet(employee.id, current_period.id)
    
    # Auto-populate from attendance records
    total_hours = db.session.query(func.sum(TimeEntry.hours)).filter(
        TimeEntry.timesheet_id == timesheet.id,
        TimeEntry.hours > 0
    ).scalar() or 0
    
    # Always look for new attendance records to add
    if populate_timesheet_from_attendance(timesheet):
        flash('Timesheet has been automatically filled with hours from attendance records.', 'success')
    
    # Redirect to the view page for this timesheet
    return redirect(url_for('timesheets.view_timesheet', timesheet_id=timesheet.id))

@timesheet_bp.route('/')
@login_required
def index():
    """Main timesheet page"""
    # Different views based on role
    if current_user.role.name in ['Admin', 'HR']:
        # Get all active pay periods for HR/Admin
        pay_periods = PayPeriod.query.order_by(PayPeriod.start_date.desc()).limit(10).all()
        
        # Get the most recent pay period to show timesheets
        recent_period = pay_periods[0] if pay_periods else None
        
        # Get timesheets for the most recent pay period
        recent_timesheets = []
        
        # For Admin/HR, always show ALL timesheets - don't filter by employee
        if recent_period:
            recent_timesheets = Timesheet.query.filter_by(pay_period_id=recent_period.id).all()
        
        # Get all employees to show in dropdown
        employees = Employee.query.filter_by(status='Active').order_by(Employee.last_name).all()
        
        return render_template(
            'timesheets/admin_view.html', 
            pay_periods=pay_periods, 
            recent_period=recent_period,
            recent_timesheets=recent_timesheets,
            employees=employees
        )
    else:
        # For regular employees, show their current timesheet
        employee = current_user.employee
        if not employee:
            flash('No employee profile associated with this account.', 'warning')
            return redirect(url_for('dashboard.index'))
        
        # Get current pay period
        current_period = get_current_pay_period()
        
        # Get employee's timesheet
        timesheet = get_employee_timesheet(employee.id, current_period.id)
        
        # Get time entries for this timesheet
        time_entries = TimeEntry.query.filter_by(timesheet_id=timesheet.id).all()
        
        # Organize entries by date
        entries_by_date = {}
        for entry in time_entries:
            entries_by_date[entry.date.strftime('%Y-%m-%d')] = entry
        
        return render_template(
            'timesheets/employee_view.html',
            employee=employee,
            timesheet=timesheet,
            pay_period=current_period,
            time_entries=entries_by_date
        )

@timesheet_bp.route('/periods')
@login_required
@role_required('Admin', 'HR')
def pay_periods():
    """Manage pay periods"""
    if PayPeriod.query.count() == 0:
        create_initial_pay_periods()
    pay_periods = PayPeriod.query.order_by(PayPeriod.start_date.desc()).all()
    return render_template('timesheets/pay_periods.html', pay_periods=pay_periods)

@timesheet_bp.route('/periods/create', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def create_pay_period():
    """Create a new pay period"""
    try:
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        if not start_date_str or not end_date_str:
            flash('Both start date and end date are required.', 'danger')
            return redirect(url_for('timesheets.pay_periods'))
            
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Validate dates
        if start_date >= end_date:
            flash('End date must be after start date.', 'danger')
            return redirect(url_for('timesheets.pay_periods'))
        
        # Check for overlapping periods
        overlapping = PayPeriod.query.filter(
            or_(
                and_(PayPeriod.start_date <= start_date, PayPeriod.end_date >= start_date),
                and_(PayPeriod.start_date <= end_date, PayPeriod.end_date >= end_date),
                and_(PayPeriod.start_date >= start_date, PayPeriod.end_date <= end_date)
            )
        ).first()
        
        if overlapping:
            flash('This pay period overlaps with an existing period.', 'danger')
            return redirect(url_for('timesheets.pay_periods'))
        
        new_period = PayPeriod(
            start_date=start_date,
            end_date=end_date,
            status='Open'
        )
        db.session.add(new_period)
        db.session.commit()
        
        flash('Pay period created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating pay period: {str(e)}', 'danger')
    
    return redirect(url_for('timesheets.pay_periods'))


@timesheet_bp.route('/periods/create-range', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def create_pay_period_range():
    """Create multiple pay periods in bulk."""
    start_date_str = request.form.get('start_date')
    count_str = request.form.get('period_count')

    if not start_date_str or not count_str:
        flash('Start date and number of periods are required.', 'danger')
        return redirect(url_for('timesheets.pay_periods'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        count = int(count_str)
        if count <= 0:
            raise ValueError('count must be positive')
    except ValueError:
        flash('Invalid input for bulk creation.', 'danger')
        return redirect(url_for('timesheets.pay_periods'))

    periods_created = 0
    for i in range(count):
        period_start = start_date + timedelta(days=14 * i)
        period_end = period_start + timedelta(days=13)

        overlapping = PayPeriod.query.filter(
            or_(
                and_(PayPeriod.start_date <= period_start, PayPeriod.end_date >= period_start),
                and_(PayPeriod.start_date <= period_end, PayPeriod.end_date >= period_end),
                and_(PayPeriod.start_date >= period_start, PayPeriod.end_date <= period_end),
            )
        ).first()

        if overlapping:
            flash(f'Period starting {period_start} overlaps with an existing period.', 'danger')
            break

        db.session.add(PayPeriod(start_date=period_start, end_date=period_end, status='Open'))
        periods_created += 1

    if periods_created:
        db.session.commit()
        flash(f'Created {periods_created} pay periods.', 'success')
    else:
        db.session.rollback()
        flash('No pay periods were created.', 'warning')

    return redirect(url_for('timesheets.pay_periods'))

@timesheet_bp.route('/periods/<int:period_id>/close', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def close_pay_period(period_id):
    """Close a pay period"""
    period = PayPeriod.query.get_or_404(period_id)
    
    if period.status == 'Closed':
        flash('This pay period is already closed.', 'warning')
    else:
        period.status = 'Closed'
        db.session.commit()
        flash('Pay period closed successfully.', 'success')
    
    return redirect(url_for('timesheets.pay_periods'))

@timesheet_bp.route('/periods/<int:period_id>/reopen', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def reopen_pay_period(period_id):
    """Reopen a closed pay period"""
    period = PayPeriod.query.get_or_404(period_id)
    
    if period.status != 'Closed':
        flash('This pay period is not closed.', 'warning')
    else:
        period.status = 'Open'
        db.session.commit()
        flash('Pay period reopened successfully.', 'success')
    
    return redirect(url_for('timesheets.pay_periods'))

@timesheet_bp.route('/periods/<int:period_id>/delete', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def delete_pay_period(period_id):
    """Delete a pay period and all associated timesheets"""
    period = PayPeriod.query.get_or_404(period_id)
    
    try:
        # First, get all timesheets for this period
        timesheets = Timesheet.query.filter_by(pay_period_id=period_id).all()
        
        # Delete all time entries for these timesheets
        for timesheet in timesheets:
            TimeEntry.query.filter_by(timesheet_id=timesheet.id).delete()
        
        # Delete the timesheets themselves
        Timesheet.query.filter_by(pay_period_id=period_id).delete()
        
        # Finally, delete the pay period
        db.session.delete(period)
        db.session.commit()
        
        flash('Pay period and all associated data deleted successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error deleting pay period: {str(e)}', 'danger')
    
    return redirect(url_for('timesheets.pay_periods'))

@timesheet_bp.route('/employee/<int:employee_id>')
@login_required
def employee_timesheets(employee_id):
    """View all timesheets for a specific employee"""
    # Check access rights
    if current_user.role.name not in ['Admin', 'HR'] and (not current_user.employee or current_user.employee.id != employee_id):
        flash('You do not have permission to view these timesheets.', 'danger')
        return redirect(url_for('timesheets.index'))
    
    employee = Employee.query.get_or_404(employee_id)
    timesheets = Timesheet.query.filter_by(employee_id=employee_id).order_by(Timesheet.created_at.desc()).all()
    
    return render_template(
        'timesheets/employee_history.html',
        employee=employee,
        timesheets=timesheets,
        now=datetime.now()
    )

@timesheet_bp.route('/period/<int:period_id>')
@login_required
@role_required('Admin', 'HR', 'Manager')
def period_timesheets(period_id):
    """View all timesheets for a specific pay period"""
    period = PayPeriod.query.get_or_404(period_id)
    
    # For managers, only show their direct reports
    if current_user.role.name == 'Manager' and current_user.employee:
        subordinates = Employee.query.filter_by(manager_id=current_user.employee.id).all()
        subordinate_ids = [s.id for s in subordinates]
        timesheets = Timesheet.query.filter(
            Timesheet.pay_period_id == period_id,
            Timesheet.employee_id.in_(subordinate_ids)
        ).all()
    else:
        # For HR/Admin, show all
        timesheets = Timesheet.query.filter_by(pay_period_id=period_id).all()
    
    return render_template(
        'timesheets/period_view.html',
        period=period,
        timesheets=timesheets
    )



def populate_timesheet_from_attendance(timesheet):
    """Utility function to populate a timesheet with attendance data
    
    This function will take a timesheet object and populate it with
    attendance data for all dates in the pay period, including
    future dates where attendance records exist.
    
    Returns: True if updates were made, False otherwise
    """
    employee_id = timesheet.employee_id
    pay_period = timesheet.pay_period
    
    # Auto-populate from attendance
    current_date = pay_period.start_date
    updates_made = False
    
    # Get existing time entries
    existing_entries = TimeEntry.query.filter_by(timesheet_id=timesheet.id).all()
    entry_dates = {entry.date.strftime('%Y-%m-%d'): entry for entry in existing_entries}
    
    # Iterate through all dates in the pay period
    while current_date <= pay_period.end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        hours = calculate_hours_from_attendance(employee_id, current_date)
        
        if hours > 0:
            # Check if entry exists for this date
            entry = entry_dates.get(date_str)
            
            if not entry:
                # Create new entry
                entry = TimeEntry(
                    timesheet_id=timesheet.id,
                    date=current_date,
                    hours=hours,
                    description="Auto-filled from attendance records"
                )
                db.session.add(entry)
                updates_made = True
            elif entry.hours == 0:
                # Update existing entry with zero hours
                entry.hours = hours
                entry.description = "Auto-filled from attendance records"
                updates_made = True
        
        current_date += timedelta(days=1)
    
    if updates_made:
        # Recalculate total hours
        timesheet.total_hours = db.session.query(func.sum(TimeEntry.hours))\
            .filter(TimeEntry.timesheet_id == timesheet.id).scalar() or 0
        db.session.commit()
        return True
    
    return False

@timesheet_bp.route('/view/<int:timesheet_id>', methods=['GET', 'POST'])
@login_required
def view_timesheet(timesheet_id):
    """View a specific timesheet with edit capabilities and navigation between employees"""
    timesheet = Timesheet.query.get_or_404(timesheet_id)
    
    # Check access rights
    if (current_user.role.name not in ['Admin', 'HR'] and 
        (not current_user.employee or current_user.employee.id != timesheet.employee_id) and
        (not current_user.employee or current_user.employee.id != timesheet.employee.manager_id)):
        flash('You do not have permission to view this timesheet.', 'danger')
        return redirect(url_for('timesheets.index'))
    
    # Find navigation links (previous and next employee)
    prev_employee = None
    next_employee = None
    
    if current_user.role.name in ['Admin', 'HR']:
        # For admin/HR, navigate through all employees
        employees = Employee.query.order_by(Employee.last_name, Employee.first_name).all()
        employee_ids = [emp.id for emp in employees]
        
        if timesheet.employee_id in employee_ids:
            current_index = employee_ids.index(timesheet.employee_id)
            
            if current_index > 0:
                prev_employee_id = employee_ids[current_index - 1]
                prev_employee = Employee.query.get(prev_employee_id)
                
            if current_index < len(employee_ids) - 1:
                next_employee_id = employee_ids[current_index + 1]
                next_employee = Employee.query.get(next_employee_id)
    
    elif current_user.employee and current_user.employee.id == timesheet.employee.manager_id:
        # For managers, navigate through their direct reports
        direct_reports = Employee.query.filter_by(manager_id=current_user.employee.id).order_by(Employee.last_name, Employee.first_name).all()
        employee_ids = [emp.id for emp in direct_reports]
        
        if timesheet.employee_id in employee_ids:
            current_index = employee_ids.index(timesheet.employee_id)
            
            if current_index > 0:
                prev_employee_id = employee_ids[current_index - 1]
                prev_employee = Employee.query.get(prev_employee_id)
                
            if current_index < len(employee_ids) - 1:
                next_employee_id = employee_ids[current_index + 1]
                next_employee = Employee.query.get(next_employee_id)
    
    # If this is a POST request and the user can edit this timesheet, process the edits
    can_edit = (current_user.employee and current_user.employee.id == timesheet.employee_id and 
                timesheet.status not in ['Submitted', 'Approved'])
    
    if request.method == 'POST' and can_edit:
        try:
            # Process each day in the pay period
            start_date = timesheet.pay_period.start_date
            end_date = timesheet.pay_period.end_date
            current_date = start_date
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                hours = request.form.get(f'hours_{date_str}', '0')
                description = request.form.get(f'description_{date_str}', '')
                
                # Find or create entry for this date
                entry = TimeEntry.query.filter_by(
                    timesheet_id=timesheet.id,
                    date=current_date
                ).first()
                
                try:
                    hours_val = float(hours) if hours else 0
                except ValueError:
                    hours_val = 0
                
                if entry:
                    # Update existing entry
                    entry.hours = hours_val
                    entry.description = description
                else:
                    # Create new entry if hours > 0 or description exists
                    if hours_val > 0 or description:
                        entry = TimeEntry(
                            timesheet_id=timesheet.id,
                            date=current_date,
                            hours=hours_val,
                            description=description
                        )
                        db.session.add(entry)
                
                current_date += timedelta(days=1)
            
            # Update total hours
            timesheet.total_hours = db.session.query(func.sum(TimeEntry.hours))\
                .filter(TimeEntry.timesheet_id == timesheet.id).scalar() or 0
            
            db.session.commit()
            flash('Timesheet updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating timesheet: {str(e)}', 'danger')
    
    # Get time entries for display
    time_entries = TimeEntry.query.filter_by(timesheet_id=timesheet.id).order_by(TimeEntry.date).all()
    
    # Organize entries by date for the form
    entries_by_date = {}
    for entry in time_entries:
        entries_by_date[entry.date.strftime('%Y-%m-%d')] = entry
        
    # Check if fill from attendance was requested
    if request.args.get('fill_from_attendance') == '1' and can_edit:
        # Use our new utility function to populate timesheet from attendance data
        if populate_timesheet_from_attendance(timesheet):
            flash('Timesheet has been filled with hours from attendance records.', 'success')
            
            # Refresh time entries after the update
            time_entries = TimeEntry.query.filter_by(timesheet_id=timesheet.id).order_by(TimeEntry.date).all()
            
            # Reorganize entries by date
            entries_by_date = {}
            for entry in time_entries:
                entries_by_date[entry.date.strftime('%Y-%m-%d')] = entry
        else:
            flash('No attendance records found to fill the timesheet.', 'info')
    
    # Generate a list of dates for the template
    date_list = []
    current_date = timesheet.pay_period.start_date
    while current_date <= timesheet.pay_period.end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)
    
    return render_template(
        'timesheets/view.html',
        timesheet=timesheet,
        time_entries=time_entries,
        entries_by_date=entries_by_date,
        date_list=date_list,
        can_edit=can_edit,
        prev_employee=prev_employee,
        next_employee=next_employee
    )

@timesheet_bp.route('/edit/<int:timesheet_id>', methods=['GET', 'POST'])
@login_required
def edit_timesheet(timesheet_id):
    """Edit a timesheet"""
    timesheet = Timesheet.query.get_or_404(timesheet_id)
    
    # Check access rights
    if (not current_user.employee or current_user.employee.id != timesheet.employee_id):
        flash('You do not have permission to edit this timesheet.', 'danger')
        return redirect(url_for('timesheets.index'))
    
    # Can't edit submitted or approved timesheets
    if timesheet.status in ['Submitted', 'Approved']:
        flash('Cannot edit a timesheet that has been submitted or approved.', 'warning')
        return redirect(url_for('timesheets.view_timesheet', timesheet_id=timesheet.id))
    
    if request.method == 'POST':
        try:
            # Process each day in the pay period
            start_date = timesheet.pay_period.start_date
            end_date = timesheet.pay_period.end_date
            current_date = start_date
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                hours = request.form.get(f'hours_{date_str}', '0')
                description = request.form.get(f'description_{date_str}', '')
                
                # Find or create entry for this date
                entry = TimeEntry.query.filter_by(
                    timesheet_id=timesheet.id,
                    date=current_date
                ).first()
                
                if not entry:
                    entry = TimeEntry(
                        timesheet_id=timesheet.id,
                        date=current_date,
                        hours=float(hours) if hours else 0,
                        description=description
                    )
                    db.session.add(entry)
                else:
                    entry.hours = float(hours) if hours else 0
                    entry.description = description
                
                current_date += timedelta(days=1)
            
            # Update total hours
            timesheet.total_hours = db.session.query(func.sum(TimeEntry.hours))\
                .filter(TimeEntry.timesheet_id == timesheet.id).scalar() or 0
            
            db.session.commit()
            flash('Timesheet updated successfully.', 'success')
            return redirect(url_for('timesheets.view_timesheet', timesheet_id=timesheet.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating timesheet: {str(e)}', 'danger')
    
    # Get time entries
    time_entries = TimeEntry.query.filter_by(timesheet_id=timesheet.id).all()
    
    # Organize entries by date
    entries_by_date = {}
    for entry in time_entries:
        entries_by_date[entry.date.strftime('%Y-%m-%d')] = entry
    
    # Check if fill from attendance was requested
    if request.args.get('fill_from_attendance') == '1':
        employee_id = timesheet.employee_id
        start_date = timesheet.pay_period.start_date
        end_date = timesheet.pay_period.end_date
        current_date = start_date
        
        updates_made = False
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Only update entries with zero hours or no entry
            if date_str not in entries_by_date or entries_by_date[date_str].hours == 0:
                hours = calculate_hours_from_attendance(employee_id, current_date)
                
                if hours > 0:
                    # Create or update entry
                    entry = entries_by_date.get(date_str, None)
                    if not entry:
                        entry = TimeEntry(
                            timesheet_id=timesheet.id,
                            date=current_date,
                            hours=hours,
                            description="Auto-filled from attendance records"
                        )
                        db.session.add(entry)
                        entries_by_date[date_str] = entry
                        updates_made = True
                    elif entry.hours == 0:
                        entry.hours = hours
                        entry.description = "Auto-filled from attendance records"
                        updates_made = True
            
            current_date += timedelta(days=1)
        
        if updates_made:
            # Update total hours
            timesheet.total_hours = db.session.query(func.sum(TimeEntry.hours))\
                .filter(TimeEntry.timesheet_id == timesheet.id).scalar() or 0
            
            db.session.commit()
            flash('Timesheet has been filled with hours from attendance records.', 'success')
        else:
            flash('No attendance records found to fill the timesheet.', 'info')
    
    # Generate a list of dates for the template
    date_list = []
    current_date = timesheet.pay_period.start_date
    while current_date <= timesheet.pay_period.end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)
    
    return render_template(
        'timesheets/edit.html',
        timesheet=timesheet,
        entries=entries_by_date,
        date_list=date_list
    )

@timesheet_bp.route('/submit/<int:timesheet_id>', methods=['POST'])
@login_required
def submit_timesheet(timesheet_id):
    """Submit a timesheet for approval"""
    timesheet = Timesheet.query.get_or_404(timesheet_id)
    
    # Check access rights
    if (not current_user.employee or current_user.employee.id != timesheet.employee_id):
        flash('You do not have permission to submit this timesheet.', 'danger')
        return redirect(url_for('timesheets.index'))
    
    # Can't submit already submitted or approved timesheets
    if timesheet.status in ['Submitted', 'Approved']:
        flash('This timesheet has already been submitted or approved.', 'warning')
        return redirect(url_for('timesheets.view_timesheet', timesheet_id=timesheet.id))
    
    try:
        # Check if there are any time entries
        entry_count = TimeEntry.query.filter_by(timesheet_id=timesheet.id).count()
        if entry_count == 0:
            flash('Cannot submit an empty timesheet. Please add time entries first.', 'warning')
            return redirect(url_for('timesheets.edit_timesheet', timesheet_id=timesheet.id))
        
        # Update timesheet status
        timesheet.status = 'Submitted'
        timesheet.submitted_at = datetime.now()
        
        # Update total hours
        timesheet.total_hours = db.session.query(func.sum(TimeEntry.hours))\
            .filter(TimeEntry.timesheet_id == timesheet.id).scalar() or 0
        
        db.session.commit()
        flash('Timesheet submitted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting timesheet: {str(e)}', 'danger')
    
    return redirect(url_for('timesheets.view_timesheet', timesheet_id=timesheet.id))

@timesheet_bp.route('/approve/<int:timesheet_id>', methods=['POST'])
@login_required
def approve_timesheet(timesheet_id):
    """Approve a submitted timesheet"""
    timesheet = Timesheet.query.get_or_404(timesheet_id)
    
    # Check access rights
    can_approve = current_user.role.name in ['Admin', 'HR']
    if not can_approve and current_user.employee:
        # Managers can approve their direct reports' timesheets
        can_approve = timesheet.employee.manager_id == current_user.employee.id
    
    if not can_approve:
        flash('You do not have permission to approve this timesheet.', 'danger')
        return redirect(url_for('timesheets.index'))
    
    # Can only approve submitted timesheets
    if timesheet.status != 'Submitted':
        flash('Only submitted timesheets can be approved.', 'warning')
        return redirect(url_for('timesheets.view_timesheet', timesheet_id=timesheet.id))
    
    try:
        # Update timesheet status
        timesheet.status = 'Approved'
        timesheet.approved_by = current_user.id
        timesheet.approved_at = datetime.now()
        timesheet.comments = request.form.get('comments', '')
        
        # Commit the approval first
        db.session.commit()
        
        # Accrue leave hours based on the approved timesheet hours
        from utils.leave_accrual import accrue_leave_from_timesheet
        accrual_results = accrue_leave_from_timesheet(timesheet.id)
        
        # If any hours were accrued, display a message
        if accrual_results and any(hours > 0 for hours in accrual_results.values()):
            accrual_messages = []
            for leave_type, hours in accrual_results.items():
                if hours > 0:
                    accrual_messages.append(f"{leave_type}: {hours:.2f} hours")
            
            if accrual_messages:
                accrual_msg = "Leave hours accrued: " + ", ".join(accrual_messages)
                flash(accrual_msg, 'info')
        
        flash('Timesheet approved successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving timesheet: {str(e)}', 'danger')
    
    return redirect(url_for('timesheets.view_timesheet', timesheet_id=timesheet.id))

@timesheet_bp.route('/reject/<int:timesheet_id>', methods=['POST'])
@login_required
def reject_timesheet(timesheet_id):
    """Reject a submitted timesheet"""
    timesheet = Timesheet.query.get_or_404(timesheet_id)
    
    # Check access rights
    can_reject = current_user.role.name in ['Admin', 'HR']
    if not can_reject and current_user.employee:
        # Managers can reject their direct reports' timesheets
        can_reject = timesheet.employee.manager_id == current_user.employee.id
    
    if not can_reject:
        flash('You do not have permission to reject this timesheet.', 'danger')
        return redirect(url_for('timesheets.index'))
    
    # Can only reject submitted timesheets
    if timesheet.status != 'Submitted':
        flash('Only submitted timesheets can be rejected.', 'warning')
        return redirect(url_for('timesheets.view_timesheet', timesheet_id=timesheet.id))
    
    try:
        # Update timesheet status
        timesheet.status = 'Rejected'
        timesheet.comments = request.form.get('comments', '')
        
        db.session.commit()
        flash('Timesheet rejected. The employee can now make changes and resubmit.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting timesheet: {str(e)}', 'danger')
    
    return redirect(url_for('timesheets.view_timesheet', timesheet_id=timesheet.id))