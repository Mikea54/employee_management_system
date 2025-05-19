from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app import db
from models import User, Role

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Validate form data
        if not username or not password:
            flash('Please enter both username and password', 'danger')
            return render_template('login.html')
        
        # Find user by username
        user = User.query.filter_by(username=username).first()
        
        # Check if user exists and password is correct
        if user and user.check_password(password):
            # Check if user is active
            if user.is_active:
                # Login user
                login_user(user)
                flash(f'Welcome back, {user.username}!', 'success')
                
                # Update last login timestamp
                user.last_login = db.func.now()
                db.session.commit()
                
                # Redirect to requested page or dashboard
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard.index'))
            else:
                flash('Your account is inactive. Please contact an administrator.', 'danger')
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    # If user is associated with an employee, redirect to employee profile
    if current_user.employee:
        return redirect(url_for('employees.view_profile', id=current_user.employee.id))
    
    # For users without employee profiles (e.g., system admins)
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/toggle-theme', methods=['POST'])
@login_required
def toggle_theme():
    """Toggle between light and dark theme."""
    # Toggle the theme preference
    theme = current_user.toggle_theme()
    
    # Save to database
    db.session.commit()
    
    # Redirect back to the referring page
    return_url = request.referrer or url_for('dashboard.index')
    
    return redirect(return_url)
