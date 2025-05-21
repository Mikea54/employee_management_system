from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from models import Employee, Department
from utils.helpers import role_required

organization_bp = Blueprint('organization', __name__, url_prefix='/organization')

@organization_bp.route('/')
@login_required
def index():
    """Main organizational chart page."""
    # Get all departments for filtering
    departments = Department.query.all()
    return render_template('organization/chart.html', departments=departments)

@organization_bp.route('/chart-data')
@login_required
def chart_data():
    """Return JSON data for organizational chart."""
    # Get filter parameters
    department_id = request.args.get('department_id', type=int)
    
    # Base query to get employees with their managers
    query = Employee.query.filter(Employee.status == 'Active')
    
    # Apply department filter if provided
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    
    employees = query.all()
    
    # Build chart data
    org_data = []
    
    for employee in employees:
        # Create node for each employee
        employee_node = {
            'id': str(employee.id),
            'name': employee.full_name,
            'title': employee.job_title,
            'department': employee.department.name if employee.department else '',
            'img': '',  # No image
        }
        
        # Add parent (manager) id
        if employee.manager_id:
            employee_node['pid'] = str(employee.manager_id)
        
        org_data.append(employee_node)
    
    return jsonify(org_data)

@organization_bp.route('/employee-count-by-department')
@login_required
@role_required('Admin', 'HR', 'Manager')
def employee_count_by_department():
    """Return employee count by department for charts."""
    departments = Department.query.all()
    data = []
    
    for department in departments:
        employee_count = Employee.query.filter_by(
            department_id=department.id,
            status='Active'
        ).count()
        
        data.append({
            'department': department.name,
            'count': employee_count
        })
    
    return jsonify(data)

@organization_bp.route('/reporting-chain/<int:employee_id>')
@login_required
def reporting_chain(employee_id):
    """Get the reporting chain for a specific employee."""
    employee = Employee.query.get_or_404(employee_id)
    
    # Build reporting chain
    chain = [employee]
    current = employee
    
    # Get all managers up the chain
    while current.manager_id:
        current = current.manager
        if current in chain:  # Avoid circular references
            break
        chain.append(current)
    
    # Format response
    result = []
    for emp in chain:
        result.append({
            'id': emp.id,
            'name': emp.full_name,
            'title': emp.job_title,
            'department': emp.department.name if emp.department else ''
        })
    
    return jsonify(result)
