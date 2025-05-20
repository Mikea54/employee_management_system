import datetime
from unittest import mock
import pytest

from app import db
from models import Role, User, Employee, PayPeriod, Payroll, PayrollEntry


@pytest.fixture
def payroll_record(app, admin_user):
    with app.app_context():
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
        return payroll.id

def test_download_payslip_returns_pdf(app, client, admin_user, payroll_record):
    client.post('/login', data={'username': 'admin', 'password': 'password'})
    payroll_id = payroll_record
    dummy_pdf = b'%PDF-1.4 dummy'
    with mock.patch.dict('sys.modules', {'pdfkit': mock.Mock(from_string=mock.Mock(return_value=dummy_pdf))}):
        resp = client.get(f'/payroll/payslips/{payroll_id}/download')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/pdf'
    assert resp.data == dummy_pdf
