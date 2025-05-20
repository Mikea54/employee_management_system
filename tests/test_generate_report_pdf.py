import datetime
import sqlalchemy
import pytest
import os
import pytest

from app import db
from models import Role, User, Employee, CompensationReport
from routes.budgeting import budgeting_bp

@pytest.fixture()
def comp_report(app, admin_user):
    with app.app_context():
        app.register_blueprint(budgeting_bp, url_prefix='/budgeting')

        employee = Employee(
            employee_id='EMP1',
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            hire_date=datetime.date.today(),
            status='Active'
        )
        db.session.add(employee)
        db.session.commit()

        report = CompensationReport(
            employee_id=employee.id,
            year=2024,
            base_salary=50000,
            total_bonus=1000,
            total_allowances=500,
            total_deductions=100,
            employer_benefit_contributions=2000,
            total_compensation=53600,
        )
        db.session.add(report)
        db.session.commit()
        return report


def test_generate_report_pdf(app, client, admin_user, comp_report):
    client.post('/login', data={'username': 'admin', 'password': 'password'})
    report = comp_report
    resp = client.get(f'/budgeting/compensation-reports/{report.id}/generate-pdf')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/pdf'

    with app.app_context():
        db.session.refresh(report)
        assert report.report_file_path
        path = os.path.join(app.root_path, report.report_file_path.lstrip('/'))
        assert os.path.exists(path)

