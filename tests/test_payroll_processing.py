import os
import datetime
import pytest

# Configure app to use in-memory SQLite before importing
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'testing'

import app
from app import db
from models import Role, User, Employee, EmployeeCompensation, PayPeriod, Payroll, PayrollEntry

@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    app.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app.app_context():
        db.drop_all()
        db.create_all()

        # Create admin role and user
        admin_role = Role(name='Admin')
        db.session.add(admin_role)
        db.session.commit()

        admin_user = User(username='admin', email='admin@example.com', role_id=admin_role.id, is_active=True)
        admin_user.set_password('password')
        db.session.add(admin_user)
        db.session.commit()

        # Create active employee with compensation
        employee = Employee(
            employee_id='EMP001',
            first_name='Test',
            last_name='Employee',
            email='employee@example.com',
            hire_date=datetime.date.today(),
            status='Active'
        )
        db.session.add(employee)
        db.session.commit()

        comp = EmployeeCompensation(
            employee_id=employee.id,
            base_salary=52000.0,
            salary_type='Annual',
            effective_date=datetime.date.today()
        )
        db.session.add(comp)
        db.session.commit()

        # Create draft pay period
        period = PayPeriod(
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=14),
            status='Draft'
        )
        db.session.add(period)
        db.session.commit()

    with app.app.test_client() as client:
        # Login as admin
        client.post('/login', data={'username': 'admin', 'password': 'password'})
        yield client, employee, period

        with app.app.app_context():
            db.session.remove()
            db.drop_all()


def test_process_pay_period(client):
    client_obj, employee, period = client
    response = client_obj.get(f'/payroll/periods/{period.id}/process')
    assert response.status_code in (302, 200)

    with app.app.app_context():
        payroll = Payroll.query.filter_by(employee_id=employee.id, pay_period_id=period.id).first()
        assert payroll is not None
        entries = [e.component_name for e in payroll.entries]
        assert 'Base Salary' in entries
        assert 'Income Tax' in entries

        db.session.refresh(period)
        assert period.status == 'Processing'
