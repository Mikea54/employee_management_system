import os
import datetime
import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'testing'

from app import create_app, db
from models import Role, User, Employee, EmployeeCompensation, PayPeriod, Payroll, PayrollEntry


app = create_app()


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.drop_all()
        db.create_all()

        admin_role = Role(name='Admin')
        db.session.add(admin_role)
        db.session.commit()

        admin_user = User(username='admin', email='admin@example.com', role_id=admin_role.id, is_active=True)
        admin_user.set_password('password')
        db.session.add(admin_user)
        db.session.commit()

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
            status='Processing'
        )
        db.session.add(period)
        db.session.commit()

        payroll = Payroll(
            employee_id=employee.id,
            pay_period_id=period.id,
            gross_pay=1000.0,
            tax_amount=200.0,
            total_deductions=50.0,
            net_pay=750.0,
            status='Pending'
        )
        db.session.add(payroll)
        db.session.commit()

        e1 = PayrollEntry(payroll_id=payroll.id, component_name='Base Salary', type='Earning', amount=1000.0)
        e2 = PayrollEntry(payroll_id=payroll.id, component_name='Income Tax', type='Deduction', amount=200.0)
        e3 = PayrollEntry(payroll_id=payroll.id, component_name='Other Deduction', type='Deduction', amount=50.0)
        db.session.add_all([e1, e2, e3])
        db.session.commit()

    with app.test_client() as client:
        client.post('/login', data={'username': 'admin', 'password': 'password'})
        yield client, payroll, (e1, e2, e3)

        with app.app_context():
            db.session.remove()
            db.drop_all()


def test_edit_payslip_updates_amounts(client):
    client_obj, payroll, entries = client
    e1, e2, e3 = entries

    data = {
        f'amount_{e1.id}': '1200',
        f'amount_{e2.id}': '240',
        f'amount_{e3.id}': '60',
    }

    resp = client_obj.post(f'/payroll/payslips/{payroll.id}/edit', data=data)
    assert resp.status_code in (302, 200)

    with app.app_context():
        updated = Payroll.query.get(payroll.id)
        assert updated.gross_pay == 1200.0
        assert updated.tax_amount == 240.0
        assert updated.total_deductions == 60.0
        assert updated.net_pay == 900.0
