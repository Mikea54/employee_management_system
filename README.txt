# Employee Management System

## Overview
This comprehensive Employee Management System is designed to streamline HR operations with robust features for employee data management, attendance tracking, leave management, payroll processing, timesheet management, and organizational structure visualization.

## System Requirements
- Python 3.8 or higher
- PostgreSQL 12 or higher
- Modern web browser with JavaScript enabled

## Installation Instructions

### 1. Setting Up the Server Environment

#### Install Required System Packages
```bash
# For Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib

# For Red Hat/CentOS
sudo yum install -y python3 python3-pip postgresql postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Database Setup

#### Create a PostgreSQL Database and User
```bash
sudo -u postgres psql
```

Inside the PostgreSQL shell:
```sql
CREATE DATABASE employee_management;
CREATE USER empadmin WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE employee_management TO empadmin;
\q
```

### 3. Application Setup

#### Clone the Repository (if using Git)
```bash
git clone [repository_url]
cd employee_management
```

#### Create and Activate a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Install Python Dependencies
```bash
pip install -r dependencies.txt
```
Note: The dependencies.txt file contains all the required Python packages for this application.

### 4. Application Configuration

#### Create a .env File
Create a file named `.env` in the root directory:
```
DATABASE_URL=postgresql://empadmin:secure_password@localhost/employee_management
SESSION_SECRET=your_secure_secret_key
PGHOST=localhost
PGPORT=5432
PGDATABASE=employee_management
PGUSER=empadmin
PGPASSWORD=secure_password
```

Replace `secure_password` with your actual PostgreSQL user password and generate a random value for `SESSION_SECRET`.

#### Initialize the Database
```bash
flask db upgrade
```

#### Run Database Migration Scripts
These scripts will set up essential database components:
```bash
python add_document_types.py
python create_pay_periods.py
python add_employee_fields.py
python add_missing_payroll_columns.py
python add_tax_amount_to_payroll.py
python migrate_leave_balance_to_hours.py
python migrate_theme.py
```

### 5. Running the Application

#### For Development
```bash
flask run --host=0.0.0.0 --port=5000
```

#### For Production
We recommend using Gunicorn as a WSGI server:
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
```

For a production environment, consider setting up a reverse proxy like Nginx:

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. Running Tests

Run the unit tests using `pytest`:
```bash
pytest
```

### 7. Default Administrative Access

When you first set up the application, a default admin account is created:
- Username: admin
- Password: admin123

**Important**: Change this password immediately after first login!

## Key Features

### Employee Management
- Comprehensive employee profiles
- Document storage for employee records
- Custom fields for employee data
- Bulk import/export via CSV or Excel

### Leave Management
- Multiple leave types (Annual, Sick, Personal, etc.)
- Approval workflows for leave requests
- Leave accrual based on tenure
- Leave balance tracking

### Attendance Tracking
- Daily attendance logging
- Reports by employee and department
- Absence tracking and management

### Organizational Structure
- Department hierarchy visualization
- Reporting structure management
- Organization chart generation

### Timesheet Management
- Two-week pay period tracking
- Multi-level approval workflow
- Overtime and leave time tracking

### Payroll Processing
- Basic pay calculation
- Bonuses and allowances
- Deductions management
- Tax calculation
- Payslip generation

### Personnel Budgeting
- Yearly cost projections
- Department-based budgeting
- Compensation forecasting

## User Roles

The system supports multiple user roles:
- Admin: Full access to all system features
- HR: Access to HR-related functions
- Manager: Department-specific access and approvals
- Employee: Personal data and self-service features

## Technical Support

If you encounter any issues during installation or usage, please contact:
[Your Support Contact Information]

## License

[License Information]