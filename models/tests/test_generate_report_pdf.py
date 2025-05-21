import os
import datetime
import sqlalchemy
import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'testing'

from app import create_app, db
from models import Role, User, Employee, CompensationReport
from routes.budgeting import budgeting_bp

app = create_app()


@pytest.fixture()
def client(tmp_path):
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_ENGINE_OPTIONS={
            'connect_args': {'check_same_thread': False},
            'poolclass': sqlalchemy.pool.StaticPool,
        },
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        app.register_blueprint(budgeting_bp, url_prefix='/budgeting')

        role = Role(name='Admin')
        db.session.add(role)
        db.session.commit()

        user = User(username='admin', email='admin@example.com', role_id=role.id, is_active=True)
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

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

    with app.test_client() as client:
        client.post('/login', data={'username': 'admin', 'password': 'password'})
        yield client, report
        with app.app_context():
            db.session.remove()
            db.drop_all()


def test_generate_report_pdf(client):
    client_obj, report = client
    resp = client_obj.get(f'/budgeting/compensation-reports/{report.id}/generate-pdf')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/pdf'

    with app.app_context():
        db.session.refresh(report)
        assert report.report_file_path
        path = os.path.join(app.root_path, report.report_file_path.lstrip('/'))
        assert os.path.exists(path)

