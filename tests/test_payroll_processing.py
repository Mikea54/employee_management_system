import datetime
import pytest

from app import db
from models import Role, User, Employee, EmployeeCompensation, PayPeriod, Payroll, PayrollEntry

@pytest.fixture
def payroll_setup(app, admin_user):
    with app.app_context():
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

        period = PayPeriod(
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=14),
            status='Draft'
        )
        db.session.add(period)
        db.session.commit()
        return employee, period


def test_process_pay_period(app, client, admin_user, payroll_setup):
    client.post('/login', data={'username': 'admin', 'password': 'password'})
    employee, period = payroll_setup
    response = client.get(f'/payroll/periods/{period.id}/process')
    assert response.status_code in (302, 200)

    with app.app_context():
        payroll = Payroll.query.filter_by(employee_id=employee.id, pay_period_id=period.id).first()
        assert payroll is not None
        entries = [e.component_name for e in payroll.entries]
        assert 'Base Salary' in entries
        assert 'Income Tax' in entries

        db.session.refresh(period)
        assert period.status == 'Processing'
