"""Utility functions for importing data from files."""
import os
import pandas as pd
from io import BytesIO
from datetime import datetime
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError
from flask import flash
from app import db
from models import Employee, Department, User, Role

def allowed_file(filename, allowed_extensions=None):
    """Check if the file extension is allowed."""
    if allowed_extensions is None:
        allowed_extensions = {'csv', 'xlsx', 'xls'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def process_employee_import(file, upload_folder):
    """Process employee import from CSV or Excel file.
    
    Args:
        file: The uploaded file object
        upload_folder: Directory to save the uploaded file temporarily
        
    Returns:
        tuple: (success_count, error_count, errors)
    """
    if file and allowed_file(file.filename):
        # Create upload directory if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Process file based on extension
        extension = filename.rsplit('.', 1)[1].lower()
        
        try:
            # Read file into DataFrame
            if extension == 'csv':
                df = pd.read_csv(file_path)
            else:  # Excel file
                df = pd.read_excel(file_path)
                
            # Clean up column names (remove whitespaces, lowercase)
            df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
            
            # Required fields
            required_fields = ['first_name', 'last_name', 'email', 'hire_date', 'job_title']
            
            # Check if required fields exist
            missing_fields = [field for field in required_fields if field not in df.columns]
            if missing_fields:
                return 0, 0, [f"Missing required fields: {', '.join(missing_fields)}"]
            
            # Prepare for import
            success_count = 0
            error_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    # Skip if mandatory fields are empty
                    if (pd.isna(row['first_name']) or pd.isna(row['last_name']) or 
                            pd.isna(row['email']) or pd.isna(row['hire_date'])):
                        errors.append(f"Row {index+2}: Missing mandatory fields")
                        error_count += 1
                        continue
                    
                    # Check if employee with this email already exists
                    existing_employee = Employee.query.filter_by(email=row['email']).first()
                    if existing_employee:
                        errors.append(f"Row {index+2}: Employee with email {row['email']} already exists")
                        error_count += 1
                        continue
                    
                    # Handle department if present
                    department_id = None
                    if 'department' in df.columns and not pd.isna(row['department']):
                        # Look up department by name
                        department = Department.query.filter_by(name=row['department']).first()
                        if department:
                            department_id = department.id
                        else:
                            # If configured to create departments
                            errors.append(f"Row {index+2}: Department '{row['department']}' not found")
                    
                    # Handle manager if present
                    manager_id = None
                    if 'manager_email' in df.columns and not pd.isna(row['manager_email']):
                        # Look up manager by email
                        manager = Employee.query.filter_by(email=row['manager_email']).first()
                        if manager:
                            manager_id = manager.id
                    
                    # Parse hire date
                    try:
                        if isinstance(row['hire_date'], str):
                            hire_date = datetime.strptime(row['hire_date'], '%Y-%m-%d').date()
                        else:
                            # Assuming it's already a datetime
                            hire_date = row['hire_date'].date()
                    except (ValueError, AttributeError):
                        errors.append(f"Row {index+2}: Invalid date format for hire_date. Use YYYY-MM-DD")
                        error_count += 1
                        continue
                    
                    # Generate employee ID (e.g., EMP-2023-001)
                    # You might want to customize this based on your requirements
                    year = datetime.now().year
                    last_employee = Employee.query.order_by(Employee.id.desc()).first()
                    if last_employee:
                        last_id = last_employee.id
                    else:
                        last_id = 0
                    
                    employee_id = f"EMP-{year}-{last_id + 1:03d}"
                    
                    # Handle new fields
                    is_manager = False
                    if 'is_manager' in row and row['is_manager']:
                        is_manager_val = str(row['is_manager']).lower()
                        is_manager = is_manager_val in ['yes', 'true', '1', 'y']
                    
                    # Parse birth date if provided
                    birth_date = None
                    if 'birth_date' in row and pd.notna(row['birth_date']):
                        try:
                            birth_date = datetime.strptime(str(row['birth_date']), '%Y-%m-%d').date()
                        except ValueError:
                            # If date format is different, we'll ignore it
                            pass
                    
                    # Create new employee
                    new_employee = Employee(
                        employee_id=employee_id,
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        email=row['email'],
                        phone=row.get('phone', None),
                        address=row.get('address', None),
                        department_id=department_id,
                        job_title=row['job_title'],
                        manager_id=manager_id,
                        hire_date=hire_date,
                        status='Active',
                        is_manager=is_manager,
                        level=row.get('level', None),
                        education_level=row.get('education_level', None),
                        birth_date=birth_date
                    )
                    
                    # Create a corresponding user account for the employee
                    username = row['email'].split('@')[0]
                    existing_user = User.query.filter_by(username=username).first()
                    if existing_user:
                        count = 1
                        while User.query.filter_by(username=f"{username}{count}").first():
                            count += 1
                        username = f"{username}{count}"

                    employee_role = Role.query.filter_by(name='Employee').first()
                    default_password = f"{employee_id}{row['last_name'][:3].lower()}"

                    new_user = User(
                        username=username,
                        email=row['email'],
                        role_id=employee_role.id if employee_role else None
                    )
                    new_user.set_password(default_password)

                    db.session.add(new_user)
                    db.session.flush()

                    new_employee.user_id = new_user.id
                    db.session.add(new_employee)
                    db.session.commit()
                    success_count += 1
                    
                except Exception as e:
                    db.session.rollback()
                    errors.append(f"Row {index+2}: {str(e)}")
                    error_count += 1
            
            return success_count, error_count, errors
            
        except Exception as e:
            return 0, 0, [f"Error processing file: {str(e)}"]
        
        finally:
            # Clean up temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    return 0, 0, ["Invalid file format. Please upload CSV or Excel file."]

def get_import_template(upload_folder, file_format='csv'):
    """Generate a template file for employee import.
    
    Args:
        upload_folder: Directory to save the template file
        file_format: 'csv' or 'xlsx'
        
    Returns:
        str: Path to the generated template file
    """
    # Create upload directory if it doesn't exist
    os.makedirs(upload_folder, exist_ok=True)
    
    # Template data
    columns = [
        'first_name', 'last_name', 'email', 'phone', 
        'address', 'department', 'job_title', 
        'manager_email', 'hire_date', 'is_manager',
        'level', 'education_level', 'birth_date'
    ]
    
    # Create empty DataFrame with columns
    df = pd.DataFrame(columns=columns)
    
    # Add example row
    example_row = {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'phone': '123-456-7890',
        'address': '123 Main St, City, State, ZIP',
        'department': 'IT',
        'job_title': 'Software Developer',
        'manager_email': 'manager@example.com',
        'hire_date': '2023-01-15',
        'is_manager': 'No',
        'level': 'Mid-Level',
        'education_level': 'Bachelor\'s Degree',
        'birth_date': '1990-05-15'
    }
    df = pd.concat([df, pd.DataFrame([example_row])], ignore_index=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    if file_format == 'csv':
        filename = f"employee_import_template_{timestamp}.csv"
        file_path = os.path.join(upload_folder, filename)
        df.to_csv(file_path, index=False)
    else:
        filename = f"employee_import_template_{timestamp}.xlsx"
        file_path = os.path.join(upload_folder, filename)
        df.to_excel(file_path, index=False)
    
    return file_path

def process_employee_bulk_update(file):
    """Process bulk updates for employee departments and managers.
    
    Args:
        file: The uploaded file (CSV or Excel)
        
    Returns:
        dict: Result with success flag, count of updated records, and errors
    """
    try:
        # Read file
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:  # Excel
            df = pd.read_excel(file)
        
        # Clean column names
        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
        
        # Check for required employee_id column
        if 'employee_id' not in df.columns:
            return {
                'success': False,
                'message': 'Missing required column: employee_id',
                'updated': 0,
                'errors': 0
            }
        
        # Process updates
        updated_count = 0
        error_messages = []
        
        for index, row in df.iterrows():
            try:
                # Skip rows without employee_id
                if pd.isna(row['employee_id']):
                    error_messages.append(f"Row {index+2}: Missing employee_id")
                    continue
                
                # Find employee
                employee = Employee.query.filter_by(employee_id=row['employee_id']).first()
                if not employee:
                    error_messages.append(f"Row {index+2}: Employee with ID '{row['employee_id']}' not found")
                    continue
                
                # Track if anything changed
                changed = False
                
                # Update is_manager flag if provided
                if 'is_manager' in df.columns and not pd.isna(row['is_manager']):
                    is_manager_val = str(row['is_manager']).lower().strip()
                    is_manager = is_manager_val in ['yes', 'true', '1', 'y']
                    
                    if employee.is_manager != is_manager:
                        employee.is_manager = is_manager
                        changed = True
                
                # Update department (by ID or name)
                if ('department_id' in df.columns and not pd.isna(row['department_id'])) or \
                   ('department_name' in df.columns and not pd.isna(row['department_name'])):
                    
                    department = None
                    
                    # Try to find department by ID first
                    if 'department_id' in df.columns and not pd.isna(row['department_id']):
                        try:
                            dept_id = int(row['department_id'])
                            department = Department.query.get(dept_id)
                        except (ValueError, TypeError):
                            error_messages.append(f"Row {index+2}: Invalid department_id format")
                    
                    # If not found or not specified, try by name
                    if department is None and 'department_name' in df.columns and not pd.isna(row['department_name']):
                        department = Department.query.filter_by(name=row['department_name']).first()
                    
                    # If department found, update employee
                    if department:
                        if employee.department_id != department.id:
                            employee.department_id = department.id
                            changed = True
                    else:
                        error_messages.append(f"Row {index+2}: Department not found")
                
                # Update manager (by ID or employee_id)
                if ('manager_id' in df.columns and not pd.isna(row['manager_id'])) or \
                   ('manager_employee_id' in df.columns and not pd.isna(row['manager_employee_id'])):
                    
                    manager = None
                    
                    # Try to find manager by ID first
                    if 'manager_id' in df.columns and not pd.isna(row['manager_id']):
                        try:
                            mgr_id = int(row['manager_id'])
                            manager = Employee.query.get(mgr_id)
                        except (ValueError, TypeError):
                            error_messages.append(f"Row {index+2}: Invalid manager_id format")
                    
                    # If not found or not specified, try by employee_id
                    if manager is None and 'manager_employee_id' in df.columns and not pd.isna(row['manager_employee_id']):
                        manager = Employee.query.filter_by(employee_id=row['manager_employee_id']).first()
                    
                    # If manager found, update employee
                    if manager:
                        # Prevent circular reporting relationships
                        if manager.id == employee.id:
                            error_messages.append(f"Row {index+2}: Cannot set employee as their own manager")
                        else:
                            if employee.manager_id != manager.id:
                                employee.manager_id = manager.id
                                changed = True
                    else:
                        error_messages.append(f"Row {index+2}: Manager not found")
                
                # Count updates
                if changed:
                    updated_count += 1
                
            except Exception as e:
                error_messages.append(f"Row {index+2}: {str(e)}")
        
        # Commit all changes at once
        if updated_count > 0:
            db.session.commit()
        
        return {
            'success': True,
            'updated': updated_count,
            'errors': len(error_messages),
            'error_messages': error_messages
        }
        
    except Exception as e:
        # Rollback if any error occurs
        db.session.rollback()
        return {
            'success': False,
            'message': str(e),
            'updated': 0,
            'errors': 1
        }