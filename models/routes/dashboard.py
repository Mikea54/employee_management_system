from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, and_, extract
from models import Employee, Department, Attendance, LeaveRequest
from app import db
from utils.helpers import role_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # Get user role for conditional rendering
    user_role = current_user.role.name
    
    # For all users: Get basic statistics
    stats = {
        'employees': Employee.query.filter_by(status='Active').count(),
        'departments': Department.query.count()
    }
    
    # For HR, Admin, or Manager roles: Get attendance statistics
    if user_role in ['Admin', 'HR', 'Manager']:
        today = datetime.now().date()
        
        # Get today's attendance numbers
        attendance_stats = {
            'present': Attendance.query.filter(
                Attendance.date == today,
                Attendance.status == 'Present'
            ).count(),
            'absent': Attendance.query.filter(
                Attendance.date == today,
                Attendance.status == 'Absent'
            ).count(),
            'late': Attendance.query.filter(
                Attendance.date == today,
                Attendance.status == 'Late'
            ).count(),
        }
        stats.update(attendance_stats)
        
        # Get pending leave requests
        if user_role in ['Admin', 'HR']:
            # For admin and HR, get all pending leave requests
            pending_leaves = LeaveRequest.query.filter_by(status='Pending').count()
        else:
            # For managers, get pending leave requests for their subordinates
            subordinate_ids = [emp.id for emp in current_user.employee.subordinates]
            pending_leaves = LeaveRequest.query.filter(
                LeaveRequest.employee_id.in_(subordinate_ids),
                LeaveRequest.status == 'Pending'
            ).count()
        
        stats['pending_leaves'] = pending_leaves
    
    # For Employee role: Get personal statistics
    if user_role == 'Employee' and current_user.employee:
        employee = current_user.employee
        
        # Get personal leave balance
        leave_stats = {
            'leave_balance': sum([balance.remaining_days for balance in employee.leave_balances])
        }
        
        # Get personal attendance status for today
        today = datetime.now().date()
        today_attendance = Attendance.query.filter_by(
            employee_id=employee.id,
            date=today
        ).first()
        
        leave_stats['attendance_today'] = today_attendance.status if today_attendance else 'Not Recorded'
        
        stats.update(leave_stats)
    
    return render_template('dashboard.html', stats=stats, user_role=user_role)

@dashboard_bp.route('/charts/department_distribution')
@login_required
@role_required('Admin', 'HR', 'Manager')
def department_distribution():
    # Query to get employee count by department
    dept_distribution = db.session.query(
        Department.name,
        func.count(Employee.id).label('employee_count')
    ).join(
        Employee, Department.id == Employee.department_id
    ).filter(
        Employee.status == 'Active'
    ).group_by(
        Department.name
    ).all()
    
    # Format data for chart.js
    labels = [dept[0] for dept in dept_distribution]
    data = [dept[1] for dept in dept_distribution]
    
    return jsonify({
        'labels': labels,
        'datasets': [{
            'label': 'Employees per Department',
            'data': data,
            'backgroundColor': [
                '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
                '#5a5c69', '#858796', '#6f42c1', '#20c9a6', '#f8f9fc'
            ]
        }]
    })

@dashboard_bp.route('/charts/monthly_attendance')
@login_required
@role_required('Admin', 'HR', 'Manager')
def monthly_attendance():
    # Get attendance data for the current month
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Query to get daily attendance counts for the month
    monthly_data = db.session.query(
        extract('day', Attendance.date).label('day'),
        func.count(Attendance.id).label('count'),
        Attendance.status
    ).filter(
        extract('month', Attendance.date) == current_month,
        extract('year', Attendance.date) == current_year
    ).group_by(
        'day',
        Attendance.status
    ).all()
    
    # Organize data by status
    days = range(1, 32)  # 1 to 31
    present_data = [0] * 31
    absent_data = [0] * 31
    late_data = [0] * 31
    
    for record in monthly_data:
        day_index = int(record.day) - 1  # Adjust to 0-based index
        if day_index < 31:  # Ensure within bounds
            if record.status == 'Present':
                present_data[day_index] = record.count
            elif record.status == 'Absent':
                absent_data[day_index] = record.count
            elif record.status == 'Late':
                late_data[day_index] = record.count
    
    return jsonify({
        'labels': list(days),
        'datasets': [
            {
                'label': 'Present',
                'data': present_data,
                'backgroundColor': 'rgba(28, 200, 138, 0.2)',
                'borderColor': 'rgba(28, 200, 138, 1)',
                'borderWidth': 1
            },
            {
                'label': 'Absent',
                'data': absent_data,
                'backgroundColor': 'rgba(231, 74, 59, 0.2)',
                'borderColor': 'rgba(231, 74, 59, 1)',
                'borderWidth': 1
            },
            {
                'label': 'Late',
                'data': late_data,
                'backgroundColor': 'rgba(246, 194, 62, 0.2)',
                'borderColor': 'rgba(246, 194, 62, 1)',
                'borderWidth': 1
            }
        ]
    })
