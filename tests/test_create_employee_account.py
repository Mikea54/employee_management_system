import datetime
import pytest

from app import db
from models import Role, User, Employee


@pytest.fixture
def employee(app, admin_user):
    """Create an employee without an account and one existing user."""
    with app.app_context():
        employee_role = Role.query.filter_by(name='Employee').first()
        if not employee_role:
            employee_role = Role(name='Employee')
            db.session.add(employee_role)
            db.session.commit()

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
        return employee

def test_create_account_route(app, client, admin_user, employee):
    client.post('/login', data={'username': 'admin', 'password': 'password'})

    with app.app_context():
        original_count = User.query.count()
        assert employee.user_id is None

    # Create account
    resp = client.post(f'/employees/create_account/{employee.id}', follow_redirects=True)
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
    resp = client.post(f'/employees/create_account/{employee.id}', follow_redirects=True)
    assert resp.status_code in (200, 302)
    assert 'already has a user account' in resp.get_data(as_text=True)

    with app.app_context():
        assert User.query.count() == new_count
