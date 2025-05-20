import os
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import abort, request, flash, redirect, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv'}

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_document(file, upload_folder):
    """Save uploaded document and return secure filename"""
    if file and allowed_file(file.filename):
        # Create upload directory if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
        
        filename = secure_filename(file.filename)
        # Add timestamp to filename to avoid duplicates
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        return unique_filename
    return None

def role_required(*roles):
    """Decorator to check user role permissions.

    Supports both single roles and lists of roles::

        @role_required('Admin')
        @role_required('Admin', 'HR')
        @role_required(['Admin', 'HR'])
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                # Preserve destination url if user needs to log in
                return redirect(url_for('auth.login', next=request.url))

            # Normalize provided roles into a flat list
            allowed_roles = []
            for role in roles:
                if isinstance(role, (list, tuple, set)):
                    allowed_roles.extend(role)
                else:
                    allowed_roles.append(role)

            user_role = getattr(current_user, 'role', None)
            if user_role is None or user_role.name not in allowed_roles:
                flash('You do not have permission to access this page.', 'danger')
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def permission_required(permission):
    """Decorator to check if the current user's role has a permission."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            if not current_user.has_permission(permission):
                flash('You do not have permission to access this page.', 'danger')
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator

def calculate_leave_days(start_date, end_date, include_weekends=False):
    """Calculate the number of leave days between two dates"""
    if start_date > end_date:
        return 0
    
    delta = end_date - start_date
    days = delta.days + 1  # Include both start and end dates
    
    if not include_weekends:
        # Subtract weekends
        days_to_subtract = 0
        for i in range(delta.days + 1):
            day = start_date + timedelta(days=i)
            if day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                days_to_subtract += 1
        days -= days_to_subtract
    
    return days

def format_date(date_obj):
    """Format date object to string"""
    if isinstance(date_obj, datetime):
        return date_obj.strftime('%Y-%m-%d %H:%M:%S')
    return date_obj.strftime('%Y-%m-%d')

def get_years_of_service(hire_date):
    """Calculate years of service for an employee"""
    if not hire_date:
        return 0
    today = datetime.now().date()
    years = today.year - hire_date.year
    
    # Adjust if the anniversary hasn't occurred yet this year
    if (today.month, today.day) < (hire_date.month, hire_date.day):
        years -= 1
    
    return years

def get_current_employee():
    """Get the employee record for the current logged-in user"""
    if not current_user.is_authenticated:
        return None

    from models import Employee
    return Employee.query.filter_by(user_id=current_user.id).first()

def format_currency(amount, currency='$'):
    """Format a number as currency"""
    if amount is None:
        return f"{currency}0.00"
    return f"{currency}{amount:,.2f}"
