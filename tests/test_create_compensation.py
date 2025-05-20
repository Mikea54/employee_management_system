import os
import datetime
import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'testing'

import app
from app import db
from models import Role, User, Employee


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
            employee_id='EMP001',
            first_name='Test',
            last_name='Employee',
            email='employee@example.com',
            hire_date=datetime.date.today(),
            status='Active'
        )
        db.session.add(employee)
        db.session.commit()

    with app.app.test_client() as client:
        client.post('/login', data={'username': 'admin', 'password': 'password'})
        yield client, employee
        with app.app.app_context():
            db.session.remove()
            db.drop_all()


def test_create_compensation_page(client):
    client_obj, employee = client
    resp = client_obj.get(f'/payroll/compensations/create?employee_id={employee.id}')
    assert resp.status_code == 200

    data = {
        'employee_id': employee.id,
        'base_salary': '50000',
        'salary_type': 'Annual',
        'effective_date': datetime.date.today().strftime('%Y-%m-%d')
    }
    resp = client_obj.post('/payroll/compensations/create', data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Compensation assigned successfully' in resp.data
