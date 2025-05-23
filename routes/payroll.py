from datetime import datetime, timedelta
from typing import List, Optional

import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, abort, send_file
from io import BytesIO
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_, case, or_, extract
from sqlalchemy.orm import aliased

from app import db
from models import (
    Employee,
    Department,
    PayPeriod,
    Payroll,
    PayrollEntry,
    SalaryComponent,
    ComponentType,
    EmployeeCompensation,
    CompensationReport,
    SalaryStructure,
    EmployeeBenefit,
    User,
    LeaveBalance,
    LeaveType,
    Benefit,
    EmployeeIncentive,
    IncentiveType,
)
from utils.helpers import role_required, get_current_employee, format_currency

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
            components = []

            compensation = EmployeeCompensation.query.filter(
                EmployeeCompensation.employee_id == employee.id,
                or_(
                    EmployeeCompensation.end_date.is_(None),
                    EmployeeCompensation.end_date >= datetime.now().date(),
                ),
            ).order_by(EmployeeCompensation.effective_date.desc()).first()

            if compensation and compensation.salary_structure_id:
                components = (
                    SalaryComponent.query.filter_by(
                        salary_structure_id=compensation.salary_structure_id,
                        is_active=True,
                    ).all()
                )
            
            total_earnings = new_payslip.gross_pay
            total_deductions = 0
            
            for component in components:
                entry_type = (
                    'Deduction'
                    if component.component_type in ['deduction', 'tax']
                    else 'Earning'
                )

                entry = PayrollEntry(
                    payroll_id=new_payslip.id,
                    component_name=component.name,
                    amount=component.value,
                    type=entry_type,
                    is_recurring=True,
                    created_by=current_user.id,
                )

                db.session.add(entry)

                if entry_type == 'Deduction':
                    total_deductions += component.value
                else:
                    total_earnings += component.value
            
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


@payroll.route('/payslips/<int:payroll_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def edit_payslip(payroll_id):
    """Edit the amounts of payroll entries for a payslip."""
    payslip = Payroll.query.get_or_404(payroll_id)

    entries = PayrollEntry.query.filter_by(payroll_id=payroll_id).order_by(PayrollEntry.id).all()

    if request.method == 'POST':
        for entry in entries:
            field = f'amount_{entry.id}'
            if field in request.form:
                try:
                    entry.amount = float(request.form.get(field, entry.amount))
                except (TypeError, ValueError):
                    entry.amount = entry.amount

        # Recalculate payslip totals
        total_earnings = sum(e.amount for e in entries if e.type == 'Earning')
        total_deductions = sum(e.amount for e in entries if e.type == 'Deduction')
        tax_entry = next((e for e in entries if e.component_name == 'Income Tax'), None)
        tax_amount = tax_entry.amount if tax_entry else 0.0

        payslip.gross_pay = total_earnings
        payslip.tax_amount = tax_amount
        payslip.total_deductions = total_deductions - tax_amount
        payslip.net_pay = total_earnings - total_deductions

        db.session.commit()
        flash('Payslip updated successfully.', 'success')
        return redirect(url_for('payroll.view_payslip', payroll_id=payroll_id))

    return render_template('payroll/edit_payslip.html', payslip=payslip, entries=entries)


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


@payroll.route('/my-compensation-report')
@login_required
def my_compensation_report():
    """View generated compensation report for the current employee."""
    employee = get_current_employee()

    if not employee:
        flash('No employee profile found for your account', 'warning')
        return redirect(url_for('payroll.index'))

    year = request.args.get('year', datetime.now().year, type=int)

    report = CompensationReport.query.filter_by(
        employee_id=employee.id,
        year=year,
        is_visible_to_employee=True,
    ).first()

    if not report:
        flash('Compensation report not available.', 'warning')
        return redirect(url_for('payroll.my_compensation'))

    return render_template(
        'payroll/my_compensation_report.html',
        employee=employee,
        report=report,
    )


@payroll.route('/salary-structures')
@login_required
@role_required('Admin', 'HR')
def salary_structures():
    """View all salary structures"""
    # Order salary structures alphabetically by name since grade/level fields
    # are no longer part of the model
    structures = SalaryStructure.query.order_by(SalaryStructure.name).all()
    
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
        name = request.form.get('name')
        base_salary_min = float(request.form.get('base_salary_min', 0))
        base_salary_max = float(request.form.get('base_salary_max', 0))
        description = request.form.get('description')
        
        # Validate input
        if base_salary_min >= base_salary_max:
            flash('Minimum salary must be less than maximum salary', 'danger')
            return redirect(url_for('payroll.create_salary_structure'))

        # Create new structure
        new_structure = SalaryStructure(
            name=name,
            base_salary_min=base_salary_min,
            base_salary_max=base_salary_max,
            description=description,
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


@payroll.route('/compensations/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def create_compensation():
    """Assign salary or hourly wage to an employee."""
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', type=int)
        base_salary = request.form.get('base_salary', type=float)
        salary_type = request.form.get('salary_type') or 'Annual'
        hours_per_week = request.form.get('hours_per_week', type=float)
        effective_date = request.form.get('effective_date')
        end_date = request.form.get('end_date')
        salary_structure_id = request.form.get('salary_structure_id', type=int)

        if not employee_id or not base_salary or not effective_date:
            flash('Please fill in all required fields', 'danger')
            return redirect(url_for('payroll.create_compensation', employee_id=employee_id))

        try:
            comp = EmployeeCompensation(
                employee_id=employee_id,
                base_salary=base_salary,
                salary_type=salary_type,
                hours_per_week=hours_per_week,
                effective_date=datetime.strptime(effective_date, '%Y-%m-%d').date(),
                end_date=datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None,
                salary_structure_id=salary_structure_id,
            )
            db.session.add(comp)
            db.session.commit()
            flash('Compensation assigned successfully', 'success')
            return redirect(url_for('employees.view_profile', id=employee_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error assigning compensation: {str(e)}', 'danger')
            return redirect(url_for('payroll.create_compensation', employee_id=employee_id))

    employee_id = request.args.get('employee_id', type=int)
    employees = Employee.query.order_by(Employee.first_name, Employee.last_name).all()
    salary_structures = SalaryStructure.query.order_by(SalaryStructure.name).all()

    return render_template(
        'payroll/create_compensation.html',
        employees=employees,
        salary_structures=salary_structures,
        selected_employee_id=employee_id,
    )


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
    
    def annual_base(comp):
        if comp.salary_type == 'Annual':
            return comp.base_salary
        hours = comp.hours_per_week or 40.0
        return comp.base_salary * hours * 52

    def annual_bonus(emp_id):
        return (
            db.session.query(func.coalesce(func.sum(EmployeeIncentive.amount), 0.0))
            .filter(EmployeeIncentive.employee_id == emp_id)
            .scalar()
            or 0.0
        )

    def annual_benefits(emp_id):
        return (
            db.session.query(func.coalesce(func.sum(Benefit.employer_contribution), 0.0))
            .join(EmployeeBenefit, EmployeeBenefit.benefit_id == Benefit.id)
            .filter(
                EmployeeBenefit.employee_id == emp_id,
                or_(EmployeeBenefit.end_date.is_(None), EmployeeBenefit.end_date >= datetime.now().date()),
            )
            .scalar()
            or 0.0
        )

    # Calculate totals using current compensation data
    total_salary = 0.0
    total_compensation = 0.0
    for emp, comp in results:
        comp.annual_salary = annual_base(comp)
        comp.total_bonus = annual_bonus(emp.id)
        comp.total_benefits = annual_benefits(emp.id)
        total_salary += comp.annual_salary
        total_compensation += comp.annual_salary + comp.total_bonus + comp.total_benefits
    
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
    
    employees = db.session.query(Employee, EmployeeCompensation)\
        .join(EmployeeCompensation, Employee.id == EmployeeCompensation.employee_id)\
        .filter(
            or_(
                EmployeeCompensation.end_date.is_(None),
                EmployeeCompensation.end_date >= datetime.now().date(),
            )
        ).all()

    def annual_base(comp):
        if comp.salary_type == 'Annual':
            return comp.base_salary
        hours = comp.hours_per_week or 40.0
        return comp.base_salary * hours * 52

    def annual_bonus(emp_id):
        return (
            db.session.query(func.coalesce(func.sum(EmployeeIncentive.amount), 0.0))
            .filter(EmployeeIncentive.employee_id == emp_id)
            .scalar()
            or 0.0
        )

    def annual_benefits(emp_id):
        return (
            db.session.query(func.coalesce(func.sum(Benefit.employer_contribution), 0.0))
            .join(EmployeeBenefit, EmployeeBenefit.benefit_id == Benefit.id)
            .filter(
                EmployeeBenefit.employee_id == emp_id,
                or_(EmployeeBenefit.end_date.is_(None), EmployeeBenefit.end_date >= datetime.now().date()),
            )
            .scalar()
            or 0.0
        )

    aggregates = {}
    for emp, comp in employees:
        category = emp.department.name if report_type == 'department' else emp.job_title
        data = aggregates.setdefault(
            category,
            {'employee_count': 0, 'total_base_pay': 0.0, 'total_bonus': 0.0, 'total_benefits': 0.0},
        )
        data['employee_count'] += 1
        data['total_base_pay'] += annual_base(comp)
        data['total_bonus'] += annual_bonus(emp.id)
        data['total_benefits'] += annual_benefits(emp.id)

    results = []
    for category, data in sorted(aggregates.items()):
        results.append(
            type(
                'Row',
                (object,),
                {
                    'category': category,
                    'employee_count': data['employee_count'],
                    'total_base_pay': data['total_base_pay'],
                    'total_bonus': data['total_bonus'],
                    'total_benefits': data['total_benefits'],
                },
            )()
        )
    
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
    
    def annual_base(comp):
        if comp.salary_type == 'Annual':
            return comp.base_salary
        hours = comp.hours_per_week or 40.0
        return comp.base_salary * hours * 52

    def annual_bonus(emp_id):
        return (
            db.session.query(func.coalesce(func.sum(EmployeeIncentive.amount), 0.0))
            .filter(EmployeeIncentive.employee_id == emp_id)
            .scalar()
            or 0.0
        )

    def annual_benefits(emp_id):
        return (
            db.session.query(func.coalesce(func.sum(Benefit.employer_contribution), 0.0))
            .join(EmployeeBenefit, EmployeeBenefit.benefit_id == Benefit.id)
            .filter(
                EmployeeBenefit.employee_id == emp_id,
                or_(EmployeeBenefit.end_date.is_(None), EmployeeBenefit.end_date >= datetime.now().date()),
            )
            .scalar()
            or 0.0
        )

    # Format data for the report
    report_data = []
    total_base = 0.0
    total_bonus = 0.0
    total_benefits = 0.0

    for employee, comp in results:
        base_pay = annual_base(comp)
        bonus_pay = annual_bonus(employee.id) if report.include_bonuses else 0.0
        benefits_pay = annual_benefits(employee.id) if report.include_benefits else 0.0

        total_comp = base_pay + bonus_pay + benefits_pay

        report_data.append({
            'employee': employee,
            'compensation': comp,
            'department': employee.department.name,
            'position': employee.job_title,
            'total_compensation': total_comp,
        })

        total_base += base_pay
        total_bonus += bonus_pay
        total_benefits += benefits_pay

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
    
    # Get payroll entries for the payslip
    entries = PayrollEntry.query.filter_by(payroll_id=payroll_id).all()
    earnings = [e for e in entries if e.type == 'Earning']
    deductions = [e for e in entries if e.type == 'Deduction']

    # Render the payslip HTML
    html = render_template(
        'payroll/view_payslip.html',
        payslip=payslip,
        earnings=earnings,
        deductions=deductions,
    )

    pdf_bytes = None

    # Attempt to generate PDF using pdfkit or WeasyPrint
    try:
        import pdfkit
        pdf_bytes = pdfkit.from_string(html, False)
    except Exception:
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html).write_pdf()
        except Exception as e:
            current_app.logger.error(f"Failed to generate payslip PDF: {e}")
            abort(500, description="Unable to generate payslip PDF")

    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'payslip_{payroll_id}.pdf'
    )


# ---------------------------------------------------------------------------
# Incentive Management
# ---------------------------------------------------------------------------

@payroll.route('/incentives')
@login_required
@role_required('Admin', 'HR')
def incentives():
    """List all employee incentives."""
    incentives = EmployeeIncentive.query.order_by(EmployeeIncentive.date_awarded.desc()).all()
    employees = Employee.query.order_by(Employee.first_name, Employee.last_name).all()
    return render_template('payroll/incentives.html', incentives=incentives, employees=employees)


@payroll.route('/incentives/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def create_incentive():
    """Create a bonus or commission record for an employee."""
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', type=int)
        incentive_type = request.form.get('incentive_type')
        amount = request.form.get('amount', type=float)
        date_awarded = request.form.get('date_awarded')
        description = request.form.get('description')

        if not employee_id or not incentive_type or amount is None:
            flash('Please provide all required fields.', 'danger')
            return redirect(url_for('payroll.create_incentive'))

        incentive = EmployeeIncentive(
            employee_id=employee_id,
            incentive_type=incentive_type,
            amount=amount,
            date_awarded=datetime.strptime(date_awarded, '%Y-%m-%d').date() if date_awarded else datetime.utcnow().date(),
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.session.add(incentive)
        db.session.commit()
        flash('Incentive recorded.', 'success')
        return redirect(url_for('payroll.incentives'))

    employees = Employee.query.order_by(Employee.first_name, Employee.last_name).all()
    return render_template('payroll/create_incentive.html', employees=employees, incentive_types=[IncentiveType.BONUS, IncentiveType.COMMISSION])
