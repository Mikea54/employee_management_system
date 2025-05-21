import os
import datetime
import pytest

# Configure in-memory SQLite before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'testing'

from app import create_app, db
from models import Role, User, Employee


app = create_app()


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.drop_all()
        db.create_all()

        admin_role = Role(name='Admin')
        employee_role = Role(name='Employee')
        db.session.add_all([admin_role, employee_role])
        db.session.commit()

        admin_user = User(username='admin', email='admin@example.com', role_id=admin_role.id, is_active=True)
        admin_user.set_password('password')
        db.session.add(admin_user)
        db.session.commit()

        # Employee that already has a user with base username 'jane'
        existing_emp = Employee(
            employee_id='EMP001',
            first_name='Existing',
            last_name='User',
            email='jane@example.org',
            hire_date=datetime.date.today(),
            status='Active'
        )
        db.session.add(existing_emp)
        db.session.commit()

        existing_user = User(username='jane', email=existing_emp.email, role_id=employee_role.id, is_active=True)
        existing_user.set_password('password')
        db.session.add(existing_user)
        db.session.commit()

        existing_emp.user_id = existing_user.id
        db.session.commit()

        # Employee without an account
        employee = Employee(
            employee_id='EMP002',
            first_name='Jane',
            last_name='Doe',
            email='jane@acme.com',
            hire_date=datetime.date.today(),
            status='Active'
        )
        db.session.add(employee)
        db.session.commit()

    with app.test_client() as client:
        client.post('/login', data={'username': 'admin', 'password': 'password'})
        yield client, employee
        with app.app_context():
            db.session.remove()
            db.drop_all()

def test_create_account_route(client):
    client_obj, employee = client

    with app.app_context():
        original_count = User.query.count()
        assert employee.user_id is None

    # Create account
    resp = client_obj.post(f'/employees/create_account/{employee.id}', follow_redirects=True)
    assert resp.status_code in (200, 302)

    with app.app_context():
        new_count = User.query.count()
        db.session.refresh(employee)
        assert new_count == original_count + 1
        assert employee.user_id is not None
        user = User.query.get(employee.user_id)
        assert user is not None
        # Username should be unique (jane1 because jane already exists)
        assert user.username == 'jane1'

    # Attempt again - should not create another user
    resp = client_obj.post(f'/employees/create_account/{employee.id}', follow_redirects=True)
    assert resp.status_code in (200, 302)
    assert 'already has a user account' in resp.get_data(as_text=True)

    with app.app_context():
        assert User.query.count() == new_count
