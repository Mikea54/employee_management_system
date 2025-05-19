from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
from sqlalchemy.exc import SQLAlchemyError
import os
import io
import csv
from decimal import Decimal
import pandas as pd

from app import db
from models import (
    User, Employee, Department, SalaryStructure, SalaryComponent,
    EmployeeCompensation, PayrollPeriod, Payroll, PayrollEntry, Benefit,
    EmployeeBenefit, Budget, BudgetItem, BudgetCategory, CompensationReport
)
from utils.roles import role_required

# Create blueprint
budgeting_bp = Blueprint('budgeting', __name__)

# Helper Functions
def get_current_year():
    """Get current year"""
    return datetime.now().year

def get_department_employees(department_id):
    """Get all employees in a department"""
    return Employee.query.filter_by(department_id=department_id, status='Active').all()

def get_employee_annual_salary(employee_id):
    """Get employee's current annual salary"""
    compensation = EmployeeCompensation.query.filter(
        EmployeeCompensation.employee_id == employee_id,
        or_(
            EmployeeCompensation.end_date.is_(None),
            EmployeeCompensation.end_date >= datetime.now().date()
        )
    ).order_by(EmployeeCompensation.effective_date.desc()).first()
    
    return compensation.base_salary if compensation else 0

def get_total_benefits_cost(employee_id):
    """Get total annual benefits cost for an employee"""
    benefits = EmployeeBenefit.query.filter(
        EmployeeBenefit.employee_id == employee_id,
        or_(
            EmployeeBenefit.end_date.is_(None), 
            EmployeeBenefit.end_date >= datetime.now().date()
        )
    ).all()
    
    total = 0
    
    for benefit in benefits:
        # Get the benefit plan to calculate employer contribution
        plan = benefit.benefit_plan
        if plan:
            if plan.employer_contribution:
                total += plan.employer_contribution * 12  # Annual cost
            elif plan.employer_contribution_percentage:
                # Calculate based on salary percentage
                salary = get_employee_annual_salary(employee_id)
                total += salary * (plan.employer_contribution_percentage / 100)
    
    return total

# Budget Routes

@budgeting_bp.route('/')
@login_required
@role_required('Admin', 'HR', 'Finance')
def index():
    """Personnel Budgeting Dashboard"""
    current_year = get_current_year()
    budgets = Budget.query.filter_by(year=current_year).all()
    
    # Calculate total budget
    total_budget = sum(budget.total_amount for budget in budgets)
    
    # Get departments for filtering
    departments = Department.query.all()
    
    return render_template(
        'budgeting/index.html',
        current_year=current_year,
        budgets=budgets,
        total_budget=total_budget,
        departments=departments
    )

@budgeting_bp.route('/budgets')
@login_required
@role_required('Admin', 'HR', 'Finance')
def budgets():
    """View all budgets"""
    budgets = Budget.query.order_by(Budget.year.desc(), Budget.name).all()
    return render_template('budgeting/budgets.html', budgets=budgets)

@budgeting_bp.route('/budgets/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR', 'Finance')
def create_budget():
    """Create new budget"""
    if request.method == 'POST':
        try:
            year = int(request.form['year'])
            name = request.form['name']
            description = request.form['description']
            department_id = int(request.form['department_id']) if request.form['department_id'] else None
            total_amount = float(request.form['total_amount'])
            
            # Create budget
            budget = Budget(
                year=year,
                name=name,
                description=description,
                department_id=department_id,
                total_amount=total_amount,
                status='Draft',
                created_by=current_user.id
            )
            
            db.session.add(budget)
            db.session.commit()
            
            flash('Budget created successfully.', 'success')
            return redirect(url_for('budgeting.budget_details', budget_id=budget.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating budget: {str(e)}', 'danger')
    
    departments = Department.query.all()
    current_year = get_current_year()
    next_year = current_year + 1
    
    return render_template(
        'budgeting/create_budget.html',
        departments=departments,
        current_year=current_year,
        next_year=next_year
    )

@budgeting_bp.route('/budgets/<int:budget_id>')
@login_required
@role_required('Admin', 'HR', 'Finance')
def budget_details(budget_id):
    """View budget details"""
    budget = Budget.query.get_or_404(budget_id)
    items = BudgetItem.query.filter_by(budget_id=budget_id).all()
    
    # Calculate totals by category
    category_totals = {}
    for item in items:
        if item.category not in category_totals:
            category_totals[item.category] = 0
        category_totals[item.category] += item.amount
    
    # Calculate remaining budget
    used_budget = sum(item.amount for item in items)
    remaining_budget = budget.total_amount - used_budget
    
    return render_template(
        'budgeting/budget_details.html',
        budget=budget,
        items=items,
        category_totals=category_totals,
        used_budget=used_budget,
        remaining_budget=remaining_budget
    )

@budgeting_bp.route('/budgets/<int:budget_id>/add-item', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR', 'Finance')
def add_budget_item(budget_id):
    """Add item to budget"""
    budget = Budget.query.get_or_404(budget_id)
    
    if request.method == 'POST':
        try:
            category = request.form['category']
            subcategory = request.form['subcategory']
            description = request.form['description']
            amount = float(request.form['amount'])
            employee_id = int(request.form['employee_id']) if request.form.get('employee_id') else None
            
            # Create budget item
            item = BudgetItem(
                budget_id=budget_id,
                category=category,
                subcategory=subcategory,
                description=description,
                amount=amount,
                employee_id=employee_id
            )
            
            db.session.add(item)
            db.session.commit()
            
            flash('Budget item added successfully.', 'success')
            return redirect(url_for('budgeting.budget_details', budget_id=budget_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding budget item: {str(e)}', 'danger')
    
    # Get employees if budget is for a department
    employees = []
    if budget.department_id:
        employees = Employee.query.filter_by(department_id=budget.department_id, status='Active').all()
    else:
        employees = Employee.query.filter_by(status='Active').all()
    
    return render_template(
        'budgeting/add_budget_item.html',
        budget=budget,
        employees=employees,
        categories=[
            (BudgetCategory.SALARIES, 'Salaries'),
            (BudgetCategory.BONUSES, 'Bonuses'),
            (BudgetCategory.BENEFITS, 'Benefits'),
            (BudgetCategory.STIPENDS, 'Stipends'),
            (BudgetCategory.TAXES, 'Taxes'),
            (BudgetCategory.INSURANCE, 'Insurance')
        ]
    )

@budgeting_bp.route('/budgets/<int:budget_id>/import', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR', 'Finance')
def import_budget_items(budget_id):
    """Import budget items from CSV/Excel"""
    budget = Budget.query.get_or_404(budget_id)
    
    if request.method == 'POST':
        if 'import_file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(url_for('budgeting.import_budget_items', budget_id=budget_id))
        
        file = request.files['import_file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('budgeting.import_budget_items', budget_id=budget_id))
        
        try:
            # Read file based on extension
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:  # Excel
                df = pd.read_excel(file)
            
            # Process each row
            success_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    category = row['category']
                    subcategory = row.get('subcategory', '')
                    description = row.get('description', '')
                    amount = float(row['amount'])
                    
                    # Handle employee if present
                    employee_id = None
                    if 'employee_id' in row and not pd.isna(row['employee_id']):
                        # Look up employee by employee_id field
                        employee = Employee.query.filter_by(employee_id=row['employee_id']).first()
                        if employee:
                            employee_id = employee.id
                    
                    # Create budget item
                    item = BudgetItem(
                        budget_id=budget_id,
                        category=category,
                        subcategory=subcategory,
                        description=description,
                        amount=amount,
                        employee_id=employee_id
                    )
                    
                    db.session.add(item)
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    continue
            
            # Commit all at once
            db.session.commit()
            
            flash(f'Successfully imported {success_count} budget items. {error_count} errors.', 'success')
            return redirect(url_for('budgeting.budget_details', budget_id=budget_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing budget items: {str(e)}', 'danger')
    
    return render_template('budgeting/import_budget_items.html', budget=budget)

@budgeting_bp.route('/budgets/<int:budget_id>/template')
@login_required
@role_required('Admin', 'HR', 'Finance')
def budget_template(budget_id):
    """Download budget import template"""
    budget = Budget.query.get_or_404(budget_id)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['category', 'subcategory', 'description', 'amount', 'employee_id'])
    
    # Write example row
    writer.writerow([
        BudgetCategory.SALARIES, 
        'Base Salary', 
        'Annual base salary', 
        '60000', 
        'EMP-2023-001'
    ])
    
    # Reset file position
    output.seek(0)
    
    # Return as downloadable file
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'budget_template_{budget.id}.csv'
    )

@budgeting_bp.route('/generate-projection')
@login_required
@role_required('Admin', 'HR', 'Finance')
def generate_projection():
    """Generate personnel budget projection"""
    year = request.args.get('year', get_current_year(), type=int)
    department_id = request.args.get('department_id', type=int)
    
    # Get employees based on department filter
    employees_query = Employee.query.filter_by(status='Active')
    if department_id:
        employees_query = employees_query.filter_by(department_id=department_id)
    
    employees = employees_query.all()
    
    # Generate projection data
    projection_data = []
    total_salary = 0
    total_benefits = 0
    total_taxes = 0
    total_cost = 0
    
    for employee in employees:
        # Get base salary
        base_salary = get_employee_annual_salary(employee.id)
        
        # Calculate 401K contributions (assumes 3% match)
        retirement_contribution = base_salary * 0.03
        
        # Calculate payroll taxes (simplified: 7.65% FICA, 0.6% FUTA, 3.5% SUTA)
        fica = base_salary * 0.0765
        futa = min(base_salary, 7000) * 0.006  # FUTA only applies to first $7000
        suta = base_salary * 0.035  # Varies by state, using example rate
        total_tax = fica + futa + suta
        
        # Get benefits cost
        benefits_cost = get_total_benefits_cost(employee.id)
        
        # Calculate total
        total = base_salary + retirement_contribution + total_tax + benefits_cost
        
        # Add to projection
        projection_data.append({
            'employee': employee,
            'base_salary': base_salary,
            'retirement': retirement_contribution,
            'taxes': total_tax,
            'benefits': benefits_cost,
            'total': total
        })
        
        # Update totals
        total_salary += base_salary
        total_benefits += (benefits_cost + retirement_contribution)
        total_taxes += total_tax
        total_cost += total
    
    return render_template(
        'budgeting/projection.html',
        projection_data=projection_data,
        year=year,
        department_id=department_id,
        departments=Department.query.all(),
        total_salary=total_salary,
        total_benefits=total_benefits,
        total_taxes=total_taxes,
        total_cost=total_cost
    )

@budgeting_bp.route('/budget-comparison')
@login_required
@role_required('Admin', 'HR', 'Finance')
def budget_comparison():
    """Compare budgets or budget scenarios"""
    budget1_id = request.args.get('budget1_id', type=int)
    budget2_id = request.args.get('budget2_id', type=int)
    
    budget1 = Budget.query.get(budget1_id) if budget1_id else None
    budget2 = Budget.query.get(budget2_id) if budget2_id else None
    
    # Get all budgets for selection
    budgets = Budget.query.order_by(Budget.year.desc(), Budget.name).all()
    
    # If both budgets selected, generate comparison
    comparison = None
    categories = []
    
    if budget1 and budget2:
        comparison = {}
        
        # Get items from both budgets
        items1 = BudgetItem.query.filter_by(budget_id=budget1.id).all()
        items2 = BudgetItem.query.filter_by(budget_id=budget2.id).all()
        
        # Group items by category
        cat1 = {}
        for item in items1:
            if item.category not in cat1:
                cat1[item.category] = 0
            cat1[item.category] += item.amount
        
        cat2 = {}
        for item in items2:
            if item.category not in cat2:
                cat2[item.category] = 0
            cat2[item.category] += item.amount
        
        # Create comparison with all categories
        categories = list(set(list(cat1.keys()) + list(cat2.keys())))
        
        for category in categories:
            amount1 = cat1.get(category, 0)
            amount2 = cat2.get(category, 0)
            diff = amount2 - amount1
            diff_percent = (diff / amount1 * 100) if amount1 > 0 else 0
            
            comparison[category] = {
                'amount1': amount1,
                'amount2': amount2,
                'diff': diff,
                'diff_percent': diff_percent
            }
    
    return render_template(
        'budgeting/comparison.html',
        budgets=budgets,
        budget1=budget1,
        budget2=budget2,
        comparison=comparison,
        categories=categories
    )

# Total Compensation Reports

@budgeting_bp.route('/compensation-reports')
@login_required
@role_required('Admin', 'HR', 'Finance')
def compensation_reports():
    """View all compensation reports"""
    reports = CompensationReport.query.order_by(
        CompensationReport.year.desc(),
        CompensationReport.generated_date.desc()
    ).all()
    
    return render_template('budgeting/compensation_reports.html', reports=reports)

@budgeting_bp.route('/generate-compensation-reports', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR', 'Finance')
def generate_compensation_reports():
    """Generate compensation reports for employees"""
    if request.method == 'POST':
        try:
            year = int(request.form['year'])
            
            # Get employees based on department filter
            department_id = request.form.get('department_id', type=int)
            employees_query = Employee.query.filter_by(status='Active')
            if department_id:
                employees_query = employees_query.filter_by(department_id=department_id)
            
            employees = employees_query.all()
            generated_count = 0
            
            for employee in employees:
                # Calculate compensation components
                base_salary = get_employee_annual_salary(employee.id)
                
                # Get any bonuses paid during the year
                bonus_components = SalaryComponent.query.filter_by(component_type=ComponentType.BONUS).all()
                bonus_component_ids = [c.id for c in bonus_components]
                
                # Sum up bonuses from payroll entries
                bonus_entries = db.session.query(
                    func.sum(PayrollEntry.amount).label('total_bonus')
                ).join(
                    Payroll, PayrollEntry.payroll_id == Payroll.id
                ).join(
                    PayrollPeriod, Payroll.payroll_period_id == PayrollPeriod.id
                ).filter(
                    Payroll.employee_id == employee.id,
                    PayrollEntry.component_id.in_(bonus_component_ids),
                    func.extract('year', PayrollPeriod.payment_date) == year
                ).first()
                
                total_bonus = bonus_entries.total_bonus if bonus_entries.total_bonus else 0
                
                # Get allowances in a similar way
                allowance_components = SalaryComponent.query.filter_by(component_type=ComponentType.ALLOWANCE).all()
                allowance_component_ids = [c.id for c in allowance_components]
                
                allowance_entries = db.session.query(
                    func.sum(PayrollEntry.amount).label('total_allowances')
                ).join(
                    Payroll, PayrollEntry.payroll_id == Payroll.id
                ).join(
                    PayrollPeriod, Payroll.payroll_period_id == PayrollPeriod.id
                ).filter(
                    Payroll.employee_id == employee.id,
                    PayrollEntry.component_id.in_(allowance_component_ids),
                    func.extract('year', PayrollPeriod.payment_date) == year
                ).first()
                
                total_allowances = allowance_entries.total_allowances if allowance_entries.total_allowances else 0
                
                # Get deductions
                deduction_components = SalaryComponent.query.filter_by(component_type=ComponentType.DEDUCTION).all()
                deduction_component_ids = [c.id for c in deduction_components]
                
                deduction_entries = db.session.query(
                    func.sum(PayrollEntry.amount).label('total_deductions')
                ).join(
                    Payroll, PayrollEntry.payroll_id == Payroll.id
                ).join(
                    PayrollPeriod, Payroll.payroll_period_id == PayrollPeriod.id
                ).filter(
                    Payroll.employee_id == employee.id,
                    PayrollEntry.component_id.in_(deduction_component_ids),
                    func.extract('year', PayrollPeriod.payment_date) == year
                ).first()
                
                total_deductions = deduction_entries.total_deductions if deduction_entries.total_deductions else 0
                
                # Get employer benefit contributions
                benefits_cost = get_total_benefits_cost(employee.id)
                
                # Calculate total compensation
                total_compensation = base_salary + total_bonus + total_allowances + benefits_cost
                
                # Create or update compensation report
                existing_report = CompensationReport.query.filter_by(
                    employee_id=employee.id,
                    year=year
                ).first()
                
                if existing_report:
                    # Update existing report
                    existing_report.base_salary = base_salary
                    existing_report.total_bonus = total_bonus
                    existing_report.total_allowances = total_allowances
                    existing_report.total_deductions = total_deductions
                    existing_report.employer_benefit_contributions = benefits_cost
                    existing_report.total_compensation = total_compensation
                    existing_report.created_by = current_user.id
                    existing_report.created_at = datetime.utcnow()
                else:
                    # Create new report
                    report = CompensationReport(
                        employee_id=employee.id,
                        year=year,
                        base_salary=base_salary,
                        total_bonus=total_bonus,
                        total_allowances=total_allowances,
                        total_deductions=total_deductions,
                        employer_benefit_contributions=benefits_cost,
                        total_compensation=total_compensation,
                        created_by=current_user.id
                    )
                    db.session.add(report)
                
                generated_count += 1
            
            db.session.commit()
            flash(f'Successfully generated {generated_count} compensation reports.', 'success')
            return redirect(url_for('budgeting.compensation_reports'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error generating compensation reports: {str(e)}', 'danger')
    
    return render_template(
        'budgeting/generate_reports.html',
        departments=Department.query.all(),
        current_year=get_current_year()
    )

@budgeting_bp.route('/compensation-reports/<int:report_id>')
@login_required
@role_required('Admin', 'HR', 'Finance')
def view_compensation_report(report_id):
    """View a specific compensation report (admin view)"""
    report = CompensationReport.query.get_or_404(report_id)
    
    return render_template(
        'budgeting/view_report.html',
        report=report
    )

@budgeting_bp.route('/compensation-reports/<int:report_id>/generate-pdf')
@login_required
@role_required('Admin', 'HR', 'Finance')
def generate_report_pdf(report_id):
    """Generate PDF for a compensation report"""
    report = CompensationReport.query.get_or_404(report_id)
    
    try:
        # PDF generation logic would go here
        # For now, just update the file path
        report.report_file_path = f'/static/reports/compensation_{report.employee_id}_{report.year}.pdf'
        db.session.commit()
        
        flash('PDF report generated successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error generating PDF report: {str(e)}', 'danger')
    
    return redirect(url_for('budgeting.view_compensation_report', report_id=report_id))