from functools import wraps
from flask import flash, redirect, url_for, current_app, request
from flask_login import current_user

def role_required(*roles):
    """
    Function decorator that ensures the current user has at least one of the specified roles.
    If the user is not authenticated or doesn't have the required role, they are redirected to the login page.
    
    Args:
        *roles: Variable number of role names that can access the decorated view
                
    Returns:
        A decorator that can be applied to flask route handlers
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            # If user doesn't have role property
            if not hasattr(current_user, 'role') or not current_user.role:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard.index'))
            
            # Check if user has any of the required roles
            if current_user.role.name not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator