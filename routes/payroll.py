from datetime import datetime, timedelta
from typing import List, Optional

import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, abort, send_file
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_, case, or_, extract
from sqlalchemy.orm import aliased

from app import db
from models import (Employee, Department, PayPeriod, Payroll, PayrollEntry, SalaryComponent,
                   ComponentType, EmployeeCompensation, CompensationReport, SalaryStructure,
                   EmployeeBenefit, User, LeaveBalance, LeaveType, Benefit)
from utils.roles import role_required
from utils.helpers import get_current_employee, format_currency

payroll = Blueprint('payroll', __name__)

@payroll.route('/')
@login_required
def index():
    """Payroll dashboard view"""
    # Get the employee record for the current user (if exists)
    employee = get_current_employee()
    
    # Get the current payroll period
    current_period = PayPeriod.query.filter(
        PayPeriod.start_date <= datetime.now(),
        PayPeriod.end_date >= datetime.now()
    ).first()
    
    # If no current period, get the most recent draft period
    if not current_period:
        current_period = PayPeriod.query.filter_by(status='Draft').order_by(PayPeriod.start_date.asc()).first()
    
    # Get upcoming periods
    upcoming_periods = PayPeriod.query.filter(
        PayPeriod.start_date > datetime.now()
    ).order_by(PayPeriod.start_date.asc()).limit(5).all()
    
    # Get past periods
    past_periods = PayPeriod.query.filter(
        PayPeriod.end_date < datetime.now()
    ).order_by(PayPeriod.end_date.desc()).limit(5).all()
    
    # For employee view - get recent payslips
    recent_payslips = None
    if employee:
        recent_payslips = Payroll.query.filter_by(employee_id=employee.id).order_by(Payroll.created_at.desc()).limit(5).all()
    
    # For admin view - get pending payslips count and employee count
    pending_count = 0
    employee_count = 0
    if current_user.has_role(['Admin', 'HR']):
        pending_count = Payroll.query.filter_by(status='Pending').count()
        employee_count = Employee.query.filter_by(status='Active').count()
    
    return render_template('payroll/index.html', 
                           employee=employee,
                           current_period=current_period,
                           upcoming_periods=upcoming_periods,
                           past_periods=past_periods,
                           recent_payslips=recent_payslips,
                           pending_count=pending_count,
                           employee_count=employee_count,
                           current_date=datetime.now().date())


@payroll.route('/periods')
@login_required
@role_required('Admin', 'HR')
def payroll_periods():
    """View all pay periods"""
    periods = PayPeriod.query.order_by(PayPeriod.start_date.desc()).all()
    
    return render_template('payroll/periods.html', periods=periods)


@payroll.route('/periods/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def create_period():
    """Create a new payroll period"""
    if request.method == 'POST':
        # Get form data
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d')
        
        # Validate dates
        if start_date >= end_date:
            flash('Start date must be before end date', 'danger')
            return redirect(url_for('payroll.create_period'))
        
        if payment_date < end_date:
            flash('Payment date should be after the end date', 'warning')
        
        # Check for overlap with existing periods
        overlapping = PayPeriod.query.filter(
            or_(
                and_(PayPeriod.start_date <= start_date, PayPeriod.end_date >= start_date),
                and_(PayPeriod.start_date <= end_date, PayPeriod.end_date >= end_date),
                and_(PayPeriod.start_date >= start_date, PayPeriod.end_date <= end_date)
            )
        ).first()
        
        if overlapping:
            flash('This period overlaps with an existing payroll period', 'danger')
            return redirect(url_for('payroll.create_period'))
        
        # Create new period
        new_period = PayPeriod(
            start_date=start_date,
            end_date=end_date,
            payment_date=payment_date,
            status='Draft'
        )
        
        try:
            db.session.add(new_period)
            db.session.commit()
            flash('Payroll period created successfully', 'success')
            return redirect(url_for('payroll.payroll_periods'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating payroll period: {str(e)}', 'danger')
            current_app.logger.error(f"Error creating period: {e}")
            return redirect(url_for('payroll.create_period'))
    
    return render_template('payroll/create_period.html')


@payroll.route('/periods/<int:period_id>')
@login_required
@role_required('Admin', 'HR')
def view_period(period_id):
    """View details of a specific payroll period"""
    period = PayPeriod.query.get_or_404(period_id)
    
    # Get all payslips for this period
    payslips = Payroll.query.filter_by(pay_period_id=period_id).all()
    
    # Calculate totals
    total_gross = sum(payslip.gross_pay for payslip in payslips) if payslips else 0
    total_net = sum(payslip.net_pay for payslip in payslips) if payslips else 0
    total_tax = sum(payslip.tax_amount for payslip in payslips) if payslips else 0
    total_deductions = sum(payslip.total_deductions for payslip in payslips) if payslips else 0
    
    # Group by department
    departments = {}
    for payslip in payslips:
        department_name = payslip.employee.department.name
        if department_name not in departments:
            departments[department_name] = {
                'count': 0,
                'total_gross': 0,
                'total_net': 0
            }
        
        departments[department_name]['count'] += 1
        departments[department_name]['total_gross'] += payslip.gross_pay
        departments[department_name]['total_net'] += payslip.net_pay
    
    return render_template('payroll/view_period.html', 
                           period=period,
                           payslips=payslips,
                           total_gross=total_gross,
                           total_net=total_net,
                           total_tax=total_tax,
                           total_deductions=total_deductions,
                           departments=departments)




@payroll.route('/run-payroll')
@login_required
@role_required('Admin', 'HR')
def run_payroll():
    """Run payroll for the current period"""
    # Get the current period
    current_period = PayPeriod.query.filter(
        PayPeriod.start_date <= datetime.now(),
        PayPeriod.end_date >= datetime.now()
    ).first()
    
    if not current_period:
        flash('No active payroll period found.', 'warning')
        return redirect(url_for('payroll.index'))
    
    # Redirect to process this period
    return redirect(url_for('payroll.process_period', period_id=current_period.id))

@payroll.route('/reports')
@login_required
@role_required('Admin', 'HR')
def payroll_reports():
    """Payroll reports dashboard"""
    # Placeholder for payroll reports page
    return render_template('payroll/reports.html')



@payroll.route('/complete-period/<int:period_id>')
@login_required
@role_required('Admin', 'HR')
def complete_period(period_id):
    """Mark a payroll period as completed"""
    period = PayPeriod.query.get_or_404(period_id)
    
    if period.status != 'Processing':
        flash('Only periods in Processing status can be completed.', 'danger')
        return redirect(url_for('payroll.view_period', period_id=period_id))
    
    try:
        # Update period status
        period.status = 'Completed'
        
        # Update all payslips to Approved status
        for payslip in period.payrolls:
            if payslip.status == 'Pending':
                payslip.status = 'Approved'
        
        db.session.commit()
        flash('Payroll period has been marked as completed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error completing period: {str(e)}', 'danger')
    
    return redirect(url_for('payroll.view_period', period_id=period_id))

@payroll.route('/create-next-period')
@login_required
@role_required('Admin', 'HR')
def create_next_period():
    """Create the next bi-weekly period based on the most recent period"""
    # Find the most recent period
    latest_period = PayPeriod.query.order_by(PayPeriod.end_date.desc()).first()
    
    if not latest_period:
        flash('No existing periods found. Please create a period manually.', 'warning')
        return redirect(url_for('payroll.create_period'))
    
    # Calculate new period dates (2 weeks after the last period)
    new_start_date = latest_period.end_date + timedelta(days=1)
    new_end_date = new_start_date + timedelta(days=13)  # 14 days total (including start day)
    new_payment_date = new_end_date + timedelta(days=5)  # 5 days after period ends
    
    try:
        # Create new period
        new_period = PayPeriod(
            start_date=new_start_date,
            end_date=new_end_date,
            payment_date=new_payment_date,
            status='Draft'
        )
        
        db.session.add(new_period)
        db.session.commit()
        
        flash('Next payroll period created successfully.', 'success')
        return redirect(url_for('payroll.view_period', period_id=new_period.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating next period: {str(e)}', 'danger')
        return redirect(url_for('payroll.payroll_periods'))

@payroll.route('/create-annual-periods')
@login_required
@role_required('Admin', 'HR')
def create_annual_periods():
    """Create all pay periods for the current year"""
    current_year = datetime.now().year
    
    # Check if periods already exist for this year
    existing_count = PayPeriod.query.filter(
        extract('year', PayPeriod.start_date) == current_year
    ).count()
    
    if existing_count > 0:
        flash(f'Pay periods already exist for {current_year}. Please review existing periods.', 'warning')
        return redirect(url_for('payroll.payroll_periods'))
    
    # Calculate first period start
    first_day = datetime(current_year, 1, 1)
    # Find the first Sunday of the year
    while first_day.weekday() != 6:  # 6 is Sunday
        first_day += timedelta(days=1)
    
    periods_created = 0
    start_date = first_day
    
    try:
        # Create 26 bi-weekly periods (one year)
        for i in range(26):
            end_date = start_date + timedelta(days=13)
            payment_date = end_date + timedelta(days=5)
            
            # Create period
            period = PayPeriod(
                start_date=start_date,
                end_date=end_date,
                payment_date=payment_date,
                status='Draft'
            )
            
            db.session.add(period)
            periods_created += 1
            
            # Next period starts one day after this period ends
            start_date = end_date + timedelta(days=1)
        
        db.session.commit()
        flash(f'Successfully created {periods_created} pay periods for {current_year}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating annual periods: {str(e)}', 'danger')
    
    return redirect(url_for('payroll.payroll_periods'))



@payroll.route('/periods/<int:period_id>/update', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def update_period(period_id):
    """Update a payroll period"""
    period = PayPeriod.query.get_or_404(period_id)
    
    # Only draft periods can be updated
    if period.status != 'Draft':
        flash('Only draft periods can be updated', 'danger')
        return redirect(url_for('payroll.view_period', period_id=period_id))
    
    if request.method == 'POST':
        # Get form data
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d')
        
        # Validate dates
        if start_date >= end_date:
            flash('Start date must be before end date', 'danger')
            return redirect(url_for('payroll.update_period', period_id=period_id))
        
        if payment_date < end_date:
            flash('Payment date should be after the end date', 'warning')
        
        # Check for overlap with existing periods (exclude this period)
        overlapping = PayPeriod.query.filter(
            PayPeriod.id != period_id,
            or_(
                and_(PayPeriod.start_date <= start_date, PayPeriod.end_date >= start_date),
                and_(PayPeriod.start_date <= end_date, PayPeriod.end_date >= end_date),
                and_(PayPeriod.start_date >= start_date, PayPeriod.end_date <= end_date)
            )
        ).first()
        
        if overlapping:
            flash('This period overlaps with an existing payroll period', 'danger')
            return redirect(url_for('payroll.update_period', period_id=period_id))
        
        # Update period
        period.start_date = start_date
        period.end_date = end_date
        period.payment_date = payment_date
        period.updated_at = datetime.now()
        
        try:
            db.session.commit()
            flash('Payroll period updated successfully', 'success')
            return redirect(url_for('payroll.view_period', period_id=period_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating payroll period: {str(e)}', 'danger')
            current_app.logger.error(f"Error updating period: {e}")
            return redirect(url_for('payroll.update_period', period_id=period_id))
    
    return render_template('payroll/update_period.html', period=period)


@payroll.route('/periods/<int:period_id>/process')
@login_required
@role_required('Admin', 'HR')
def process_period(period_id):
    """Process a payroll period - generate payslips for all employees"""
    period = PayPeriod.query.get_or_404(period_id)
    
    # Only draft periods can be processed
    if period.status != 'Draft':
        flash('Only draft periods can be processed', 'danger')
        return redirect(url_for('payroll.view_period', period_id=period_id))
    
    # Get all active employees
    employees = Employee.query.filter_by(status='Active').all()
    
    if not employees:
        flash('No active employees found', 'warning')
        return redirect(url_for('payroll.view_period', period_id=period_id))
    
    try:
        # Loop through each employee and create a payslip
        for employee in employees:
            # Check if a payslip already exists for this employee in this period
            existing_payslip = Payroll.query.filter_by(
                employee_id=employee.id,
                pay_period_id=period.id
            ).first()
            
            if existing_payslip:
                continue  # Skip if payslip already exists
            
            # Create new payslip
            new_payslip = Payroll(
                employee_id=employee.id,
                pay_period_id=period.id,
                gross_pay=employee.base_salary / 26 if employee.salary_type == 'Annual' else employee.base_salary,  # Biweekly for annual salaries
                tax_amount=0,  # Will be calculated in the next step
                net_pay=0,     # Will be calculated in the next step
                status='Pending',
                created_by=current_user.id
            )
            
            db.session.add(new_payslip)
            db.session.flush()  # Get the ID without committing
            
            # Add base salary as a payroll entry
            base_entry = PayrollEntry(
                payroll_id=new_payslip.id,
                component_name='Base Salary',
                amount=new_payslip.gross_pay,
                type='Earning',
                is_recurring=True,
                created_by=current_user.id
            )
            
            db.session.add(base_entry)
            
            # Add any recurring salary components for this employee
            components = SalaryComponent.query.filter_by(
                employee_id=employee.id,
                is_recurring=True,
                is_active=True
            ).all()
            
            total_earnings = new_payslip.gross_pay
            total_deductions = 0
            
            for component in components:
                entry = PayrollEntry(
                    payroll_id=new_payslip.id,
                    component_name=component.name,
                    amount=component.amount,
                    type=component.type.value,
                    is_recurring=True,
                    created_by=current_user.id
                )
                
                db.session.add(entry)
                
                if component.type == ComponentType.EARNING:
                    total_earnings += component.amount
                elif component.type == ComponentType.DEDUCTION:
                    total_deductions += component.amount
            
            # Simple tax calculation (would be more complex in a real system)
            tax_rate = 0.2  # 20% tax rate
            tax_amount = total_earnings * tax_rate
            
            # Update payslip
            new_payslip.gross_pay = total_earnings
            new_payslip.tax_amount = tax_amount
            new_payslip.deductions = total_deductions
            new_payslip.net_pay = total_earnings - tax_amount - total_deductions
            
            # Add tax as a deduction entry
            tax_entry = PayrollEntry(
                payroll_id=new_payslip.id,
                component_name='Income Tax',
                amount=tax_amount,
                type='Deduction',
                is_recurring=True,
                created_by=current_user.id
            )
            
            db.session.add(tax_entry)
        
        # Update period status
        period.status = 'Processing'
        period.updated_at = datetime.now()
        
        db.session.commit()
        flash('Payroll period processed successfully. Payslips have been generated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing payroll: {str(e)}', 'danger')
        current_app.logger.error(f"Error processing payroll: {e}")
    
    return redirect(url_for('payroll.view_period', period_id=period_id))


@payroll.route('/payslips')
@login_required
@role_required('Admin', 'HR')
def payslips():
    """View all payslips (admin view)"""
    # Get filter parameters
    period_id = request.args.get('period_id', type=int)
    department_id = request.args.get('department_id', type=int)
    status = request.args.get('status')
    
    # Base query
    query = Payroll.query.join(Employee).join(PayPeriod)
    
    # Apply filters
    if period_id:
        query = query.filter(Payroll.pay_period_id == period_id)
    
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    
    if status:
        query = query.filter(Payroll.status == status)
    
    # Order by most recent periods first, then by employee name
    query = query.order_by(PayPeriod.start_date.desc(), Employee.first_name, Employee.last_name)
    
    payslips = query.all()
    
    # Get all periods and departments for filters
    periods = PayPeriod.query.order_by(PayPeriod.start_date.desc()).all()
    departments = Department.query.order_by(Department.name).all()
    
    return render_template('payroll/payslips.html', 
                           payslips=payslips,
                           periods=periods,
                           departments=departments,
                           selected_period_id=period_id,
                           selected_department_id=department_id,
                           selected_status=status)


@payroll.route('/payslips/<int:payroll_id>')
@login_required
def view_payslip(payroll_id):
    """View a specific payslip"""
    payslip = Payroll.query.get_or_404(payroll_id)
    
    # Check permissions (only admin/HR or the employee themselves)
    is_admin_or_hr = current_user.role and current_user.role.name in ['Admin', 'HR']
    is_owner = current_user.employee and current_user.employee.id == payslip.employee_id
    
    if not (is_admin_or_hr or is_owner):
        abort(403)  # Forbidden
    
    # Get payroll entries
    entries = PayrollEntry.query.filter_by(payroll_id=payroll_id).all()
    
    # Organize entries by type
    earnings = [entry for entry in entries if entry.type == 'Earning']
    deductions = [entry for entry in entries if entry.type == 'Deduction']
    
    return render_template('payroll/view_payslip.html', 
                           payslip=payslip,
                           earnings=earnings,
                           deductions=deductions)


@payroll.route('/my-payslips')
@login_required
def my_payslips():
    """View all payslips for the current employee"""
    employee = get_current_employee()
    
    if not employee:
        flash('No employee profile found for your account', 'warning')
        return redirect(url_for('payroll.index'))
    
    payslips = Payroll.query.filter_by(employee_id=employee.id).order_by(Payroll.created_at.desc()).all()

    current_period = PayPeriod.query.filter(
        PayPeriod.start_date <= datetime.now(),
        PayPeriod.end_date >= datetime.now()
    ).first()

    if not current_period:
        current_period = PayPeriod.query.filter_by(status='Draft').order_by(PayPeriod.start_date.asc()).first()

    return render_template('payroll/my_payslips.html',
                           employee=employee,
                           payslips=payslips,
                           current_period=current_period,
                           current_date=datetime.now().date())


@payroll.route('/my-compensation')
@login_required
def my_compensation():
    """View total compensation for the current employee"""
    employee = get_current_employee()
    
    if not employee:
        flash('No employee profile found for your account', 'warning')
        return redirect(url_for('payroll.index'))
    
    # Get all payroll history
    payroll_history = Payroll.query.filter_by(employee_id=employee.id).order_by(Payroll.created_at.desc()).all()
    
    # Get compensation components
    # Determine the employee's active compensation record to load the
    # associated salary structure components. SalaryComponent no longer has
    # a direct employee_id column, so we fetch components via the
    # employee's salary structure if available.
    components = []
    compensation = EmployeeCompensation.query.filter(
        EmployeeCompensation.employee_id == employee.id,
        or_(
            EmployeeCompensation.end_date.is_(None),
            EmployeeCompensation.end_date >= datetime.now().date(),
        )
    ).order_by(EmployeeCompensation.effective_date.desc()).first()

    if compensation and compensation.salary_structure_id:
        components = (
            SalaryComponent.query.filter_by(
                salary_structure_id=compensation.salary_structure_id,
                is_active=True,
            ).all()
        )
    
    # Get benefits
    try:
        benefits = db.session.query(
            Benefit, EmployeeBenefit
        ).join(
            EmployeeBenefit, EmployeeBenefit.benefit_id == Benefit.id
        ).filter(
            EmployeeBenefit.employee_id == employee.id,
            or_(EmployeeBenefit.end_date.is_(None), EmployeeBenefit.end_date >= datetime.now())
        ).all()
    except Exception as e:
        benefits = []
        flash(f"Could not load benefits: {str(e)}", "warning")
    
    return render_template('payroll/my_compensation.html',
                          employee=employee,
                          payroll_history=payroll_history,
                          components=components,
                          benefits=benefits)


@payroll.route('/salary-structures')
@login_required
@role_required('Admin', 'HR')
def salary_structures():
    """View all salary structures"""
    structures = SalaryStructure.query.order_by(SalaryStructure.grade, SalaryStructure.level).all()
    
    department_filter = request.args.get('department_id', type=int)
    
    # Get departments for filter
    departments = Department.query.order_by(Department.name).all()
    
    # Get employees assigned to each structure, with department filter if specified
    for structure in structures:
        query = Employee.query.filter_by(salary_structure_id=structure.id)
        
        if department_filter:
            query = query.filter_by(department_id=department_filter)
        
        structure.employees = query.all()
        structure.employee_count = len(structure.employees)
    
    return render_template('payroll/salary_structures.html', 
                           structures=structures,
                           departments=departments,
                           selected_department_id=department_filter)


@payroll.route('/salary-structures/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def create_salary_structure():
    """Create a new salary structure"""
    if request.method == 'POST':
        # Get form data
        grade = request.form.get('grade')
        level = request.form.get('level')
        name = request.form.get('name')
        min_salary = float(request.form.get('min_salary', 0))
        max_salary = float(request.form.get('max_salary', 0))
        midpoint = float(request.form.get('midpoint', 0))
        description = request.form.get('description')
        
        # Validate input
        if min_salary >= max_salary:
            flash('Minimum salary must be less than maximum salary', 'danger')
            return redirect(url_for('payroll.create_salary_structure'))
        
        # If midpoint not provided, calculate it
        if not midpoint:
            midpoint = (min_salary + max_salary) / 2
        
        # Create new structure
        new_structure = SalaryStructure(
            grade=grade,
            level=level,
            name=name,
            min_salary=min_salary,
            max_salary=max_salary,
            midpoint=midpoint,
            description=description,
            created_by=current_user.id
        )
        
        try:
            db.session.add(new_structure)
            db.session.commit()
            flash('Salary structure created successfully', 'success')
            return redirect(url_for('payroll.salary_structures'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating salary structure: {str(e)}', 'danger')
            return redirect(url_for('payroll.create_salary_structure'))
    
    return render_template('payroll/create_salary_structure.html')


@payroll.route('/salary-components')
@login_required
@role_required('Admin', 'HR')
def salary_components():
    """View all salary components"""
    # Get filter parameters
    component_type = request.args.get('type')
    employee_id = request.args.get('employee_id', type=int)
    
    # Base query
    query = SalaryComponent.query
    
    # Apply filters
    if component_type:
        query = query.filter(SalaryComponent.type == ComponentType[component_type])
    
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    
    components = query.order_by(SalaryComponent.employee_id, SalaryComponent.type).all()
    
    # Get employees for filter
    employees = Employee.query.order_by(Employee.first_name, Employee.last_name).all()
    
    # Get component types for filter
    component_types = [t.name for t in ComponentType]
    
    return render_template('payroll/salary_components.html', 
                           components=components,
                           employees=employees,
                           component_types=component_types,
                           selected_type=component_type,
                           selected_employee_id=employee_id)


@payroll.route('/salary-components/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def create_salary_component():
    """Create a new salary component"""
    if request.method == 'POST':
        # Get form data
        employee_id = request.form.get('employee_id', type=int)
        name = request.form.get('name')
        amount = float(request.form.get('amount', 0))
        component_type = request.form.get('type')
        is_recurring = request.form.get('is_recurring') == 'on'
        is_taxable = request.form.get('is_taxable') == 'on'
        description = request.form.get('description')
        
        # Validate input
        if not employee_id or not name or amount <= 0:
            flash('Please fill in all required fields with valid values', 'danger')
            return redirect(url_for('payroll.create_salary_component'))
        
        # Create new component
        new_component = SalaryComponent(
            employee_id=employee_id,
            name=name,
            amount=amount,
            type=ComponentType[component_type],
            is_recurring=is_recurring,
            is_taxable=is_taxable,
            description=description,
            created_by=current_user.id
        )
        
        try:
            db.session.add(new_component)
            db.session.commit()
            flash('Salary component created successfully', 'success')
            return redirect(url_for('payroll.salary_components'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating salary component: {str(e)}', 'danger')
            return redirect(url_for('payroll.create_salary_component'))
    
    # Get employees
    employees = Employee.query.order_by(Employee.first_name, Employee.last_name).all()
    
    # Get component types
    component_types = [t.name for t in ComponentType]
    
    return render_template('payroll/create_salary_component.html',
                          employees=employees,
                          component_types=component_types)


@payroll.route('/compensations')
@login_required
@role_required('Admin', 'HR')
def compensations():
    """View all employee compensations"""
    # Get filter parameters
    department_id = request.args.get('department_id', type=int)
    
    # Base query joining employee and compensation
    query = db.session.query(Employee, EmployeeCompensation)\
        .join(EmployeeCompensation, Employee.id == EmployeeCompensation.employee_id)
    
    # Apply filters
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    
    # Order by department, then name
    query = query.order_by(Employee.department_id, Employee.first_name, Employee.last_name)
    
    results = query.all()
    
    # Get departments for filter
    departments = Department.query.order_by(Department.name).all()
    
    # Calculate totals
    total_salary = sum(comp.base_pay_annual for _, comp in results)
    total_compensation = sum(comp.base_pay_annual + (comp.bonus_annual or 0) + comp.total_benefits_annual for _, comp in results)
    
    return render_template('payroll/compensations.html', 
                           results=results,
                           departments=departments,
                           selected_department_id=department_id,
                           total_salary=total_salary,
                           total_compensation=total_compensation)


@payroll.route('/compensation-reports')
@login_required
@role_required('Admin', 'HR')
def compensation_reports():
    """View compensation reports"""
    # Get filter parameters
    report_type = request.args.get('type', 'department')
    
    if report_type == 'department':
        # Department compensation summary
        results = db.session.query(
            Department.name.label('category'),
            func.count(Employee.id).label('employee_count'),
            func.sum(EmployeeCompensation.base_pay_annual).label('total_base_pay'),
            func.sum(EmployeeCompensation.bonus_annual).label('total_bonus'),
            func.sum(EmployeeCompensation.total_benefits_annual).label('total_benefits')
        ).join(Employee, Department.id == Employee.department_id)\
         .join(EmployeeCompensation, Employee.id == EmployeeCompensation.employee_id)\
         .group_by(Department.name)\
         .order_by(Department.name)\
         .all()
    else:
        # Position compensation summary
        results = db.session.query(
            Employee.position.label('category'),
            func.count(Employee.id).label('employee_count'),
            func.sum(EmployeeCompensation.base_pay_annual).label('total_base_pay'),
            func.sum(EmployeeCompensation.bonus_annual).label('total_bonus'),
            func.sum(EmployeeCompensation.total_benefits_annual).label('total_benefits')
        ).join(EmployeeCompensation, Employee.id == EmployeeCompensation.employee_id)\
         .group_by(Employee.position)\
         .order_by(Employee.position)\
         .all()
    
    # Calculate additional metrics for each result
    report_data = []
    for result in results:
        total_comp = result.total_base_pay + result.total_bonus + result.total_benefits
        avg_base = result.total_base_pay / result.employee_count if result.employee_count > 0 else 0
        avg_total = total_comp / result.employee_count if result.employee_count > 0 else 0
        
        report_data.append({
            'category': result.category,
            'employee_count': result.employee_count,
            'total_base_pay': result.total_base_pay,
            'total_bonus': result.total_bonus,
            'total_benefits': result.total_benefits,
            'total_compensation': total_comp,
            'avg_base_pay': avg_base,
            'avg_total_comp': avg_total
        })
    
    # Calculate grand totals
    grand_total = {
        'employee_count': sum(item['employee_count'] for item in report_data),
        'total_base_pay': sum(item['total_base_pay'] for item in report_data),
        'total_bonus': sum(item['total_bonus'] for item in report_data),
        'total_benefits': sum(item['total_benefits'] for item in report_data),
        'total_compensation': sum(item['total_compensation'] for item in report_data)
    }
    
    if grand_total['employee_count'] > 0:
        grand_total['avg_base_pay'] = grand_total['total_base_pay'] / grand_total['employee_count']
        grand_total['avg_total_comp'] = grand_total['total_compensation'] / grand_total['employee_count']
    else:
        grand_total['avg_base_pay'] = 0
        grand_total['avg_total_comp'] = 0
    
    return render_template('payroll/compensation_reports.html', 
                           report_type=report_type,
                           report_data=report_data,
                           grand_total=grand_total)


@payroll.route('/generate-compensation-report', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def generate_compensation_report():
    """Generate a custom compensation report"""
    if request.method == 'POST':
        # Get form data
        report_name = request.form.get('report_name')
        report_type = request.form.get('report_type')
        include_benefits = request.form.get('include_benefits') == 'on'
        include_bonuses = request.form.get('include_bonuses') == 'on'
        department_id = request.form.get('department_id', type=int)
        
        # Create report record
        new_report = CompensationReport(
            name=report_name,
            report_type=report_type,
            include_benefits=include_benefits,
            include_bonuses=include_bonuses,
            department_id=department_id,
            created_by=current_user.id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        try:
            db.session.add(new_report)
            db.session.commit()
            
            # Redirect to view the report
            flash('Compensation report generated successfully', 'success')
            return redirect(url_for('payroll.view_compensation_report', report_id=new_report.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error generating report: {str(e)}', 'danger')
            return redirect(url_for('payroll.generate_compensation_report'))
    
    # Get departments for filter
    departments = Department.query.order_by(Department.name).all()
    
    return render_template('payroll/generate_report.html', departments=departments)


@payroll.route('/compensation-reports/<int:report_id>')
@login_required
@role_required('Admin', 'HR')
def view_compensation_report(report_id):
    """View a specific compensation report"""
    report = CompensationReport.query.get_or_404(report_id)
    
    # Base query joining employee and compensation
    query = db.session.query(Employee, EmployeeCompensation)\
        .join(EmployeeCompensation, Employee.id == EmployeeCompensation.employee_id)
    
    # Apply filters from the report
    if report.department_id:
        query = query.filter(Employee.department_id == report.department_id)
    
    # Order by department, then name
    query = query.order_by(Employee.department_id, Employee.first_name, Employee.last_name)
    
    results = query.all()
    
    # Format data for the report
    report_data = []
    for employee, comp in results:
        total_comp = comp.base_pay_annual
        
        if report.include_bonuses:
            total_comp += comp.bonus_annual or 0
        
        if report.include_benefits:
            total_comp += comp.total_benefits_annual or 0
        
        report_data.append({
            'employee': employee,
            'compensation': comp,
            'department': employee.department.name,
            'position': employee.position,
            'total_compensation': total_comp
        })
    
    # Calculate totals
    total_base = sum(comp.base_pay_annual for _, comp in results)
    total_bonus = sum(comp.bonus_annual or 0 for _, comp in results) if report.include_bonuses else 0
    total_benefits = sum(comp.total_benefits_annual or 0 for _, comp in results) if report.include_benefits else 0
    total_comp = total_base + total_bonus + total_benefits
    
    return render_template('payroll/view_report.html', 
                           report=report,
                           report_data=report_data,
                           total_base=total_base,
                           total_bonus=total_bonus,
                           total_benefits=total_benefits,
                           total_comp=total_comp)


@payroll.route('/payslips/<int:payroll_id>/download')
@login_required
def download_payslip(payroll_id):
    """Download a payslip as PDF"""
    payslip = Payroll.query.get_or_404(payroll_id)
    
    # Check permissions (only admin/HR or the employee themselves)
    is_admin_or_hr = current_user.role and current_user.role.name in ['Admin', 'HR']
    is_owner = current_user.employee and current_user.employee.id == payslip.employee_id
    
    if not (is_admin_or_hr or is_owner):
        abort(403)  # Forbidden
    
    # This would be where you generate a PDF
    # For now, we'll just show a message
    flash('Payslip PDF download functionality is not implemented yet', 'info')
    return redirect(url_for('payroll.view_payslip', payroll_id=payroll_id))