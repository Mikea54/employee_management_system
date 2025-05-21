"""Utility functions for leave accrual."""
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from app import db
from models import Timesheet, LeaveBalance, LeaveType, Employee

def get_accrual_rate_by_tenure(employee_id):
    """Calculate the appropriate accrual rate based on employee tenure.
    
    For employees with less than 5 years: 2.80 hours per 40 hours worked
    For employees with 5+ years: 3.80 hours per 40 hours worked
    
    Args:
        employee_id: The employee's ID
        
    Returns:
        float: The appropriate accrual rate (hours per 40 hours worked)
    """
    employee = Employee.query.get(employee_id)
    if not employee:
        return 2.80  # Default if employee not found
    
    # Calculate tenure in years
    today = date.today()
    hire_date = employee.hire_date
    
    if not hire_date:
        return 2.80  # Default if hire date not available
    
    # Calculate years of service
    years_of_service = relativedelta(today, hire_date).years
    
    # Return appropriate accrual rate
    if years_of_service >= 5:
        return 3.80  # Higher rate for 5+ years of service
    else:
        return 2.80  # Standard rate for less than 5 years

def accrue_leave_from_timesheet(timesheet_id):
    """Accrue leave hours based on timesheet hours.
    
    Args:
        timesheet_id: ID of the approved timesheet
        
    Returns:
        Dictionary with leave type names as keys and hours accrued as values
    """
    # Get the timesheet
    timesheet = Timesheet.query.get(timesheet_id)
    if not timesheet or timesheet.status != 'Approved':
        return None
    
    # Get employee and total hours
    employee_id = timesheet.employee_id
    total_hours = timesheet.total_hours
    
    if total_hours <= 0:
        return None
    
    # Get the current year
    current_year = datetime.now().year
    
    # Get all leave types that are available for accrual
    leave_types = LeaveType.query.filter_by(is_paid=True).all()
    
    accrual_results = {}
    
    # For each leave type, accrue hours
    for leave_type in leave_types:
        # Get or create balance for this employee, leave type, and year
        balance = LeaveBalance.query.filter_by(
            employee_id=employee_id,
            leave_type_id=leave_type.id,
            year=current_year
        ).first()
        
        # Calculate appropriate accrual rate based on tenure
        accrual_rate = get_accrual_rate_by_tenure(employee_id)
        
        if not balance:
            # Create a new balance if one doesn't exist
            balance = LeaveBalance(
                employee_id=employee_id,
                leave_type_id=leave_type.id,
                year=current_year,
                total_hours=0,
                used_hours=0,
                accrual_rate=accrual_rate  # Tenure-based accrual rate
            )
            db.session.add(balance)
        else:
            # Update the accrual rate for existing balance based on current tenure
            balance.accrual_rate = accrual_rate
        
        # Calculate and apply accrual
        hours_accrued = balance.accrue_from_timesheet(total_hours)
        
        # Record the result
        accrual_results[leave_type.name] = hours_accrued
    
    # Commit changes
    db.session.commit()
    
    return accrual_results
