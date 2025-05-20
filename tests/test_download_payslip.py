import os
import datetime
from unittest import mock
import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'testing'

import app
from app import db
from models import Role, User, Employee, PayPeriod, Payroll, PayrollEntry


@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    app.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app.app_context():
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
            employee_id='EMP1',
            first_name='Test',
            last_name='Employee',
            email='emp@example.com',
            hire_date=datetime.date.today(),
            status='Active'
        )
        db.session.add(employee)
        db.session.commit()

        period = PayPeriod(
            start_date=datetime.date.today(),
            end_date=datetime.date.today(),
            status='Open'
        )
        db.session.add(period)
        db.session.commit()

        payroll = Payroll(
            employee_id=employee.id,
            pay_period_id=period.id,
            gross_pay=100.0,
            tax_amount=10.0,
            total_deductions=5.0,
            net_pay=85.0,
            status='Paid'
        )
        db.session.add(payroll)
        db.session.commit()

        entry = PayrollEntry(
            payroll_id=payroll.id,
            component_name='Base Salary',
            type='Earning',
            amount=100.0
        )
        db.session.add(entry)
        db.session.commit()

    with app.app.test_client() as client:
        client.post('/login', data={'username': 'admin', 'password': 'password'})
        yield client, payroll.id
        with app.app.app_context():
            db.session.remove()
            db.drop_all()

def test_download_payslip_returns_pdf(client):
    client_obj, payroll_id = client
    dummy_pdf = b'%PDF-1.4 dummy'
    with mock.patch.dict('sys.modules', {'pdfkit': mock.Mock(from_string=mock.Mock(return_value=dummy_pdf))}):
        resp = client_obj.get(f'/payroll/payslips/{payroll_id}/download')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/pdf'
    assert resp.data == dummy_pdf
