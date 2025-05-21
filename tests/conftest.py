import os
import types
import sys
import pytest

# Ensure tests use in-memory database before the application is imported
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SESSION_SECRET', 'testing')
os.environ.setdefault('SECRET_KEY', 'testing-secret')

sys.modules.setdefault('pandas', types.ModuleType('pandas'))

from app import create_app, db
import sqlalchemy
from datetime import date
from models import Role, User, Employee

@pytest.fixture()
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_ENGINE_OPTIONS={
            'connect_args': {'check_same_thread': False},
            'poolclass': sqlalchemy.pool.StaticPool,
        },
    )
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def admin_user(app):
    with app.app_context():
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(name='Admin')
            db.session.add(admin_role)
            db.session.commit()
        user = User.query.filter_by(username='admin').first()
        if not user:
            user = User(username='admin', email='admin@example.com', role_id=admin_role.id, is_active=True)
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture()
def user_without_employee(app):
    """Create a user who has no associated Employee record."""
    with app.app_context():
        role = Role.query.filter_by(name='Employee').first()
        if not role:
            role = Role(name='Employee')
            db.session.add(role)
            db.session.commit()

        user = User.query.filter_by(username='noemp').first()
        if not user:
            user = User(
                username='noemp',
                email='noemp@example.com',
                role_id=role.id,
                is_active=True,
            )
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture()
def user_with_employee(app):
    """Create a user and an associated Employee record."""
    with app.app_context():
        role = Role.query.filter_by(name='Employee').first()
        if not role:
            role = Role(name='Employee')
            db.session.add(role)
            db.session.commit()

        user = User.query.filter_by(username='empuser').first()
        if not user:
            user = User(
                username='empuser',
                email='empuser@example.com',
                role_id=role.id,
                is_active=True,
            )
            user.set_password('password')
            db.session.add(user)
            db.session.commit()

        employee = Employee.query.filter_by(user_id=user.id).first()
        if not employee:
            employee = Employee(
                employee_id='EMPTEST',
                first_name='Emp',
                last_name='User',
                email='empuser@example.com',
                hire_date=date.today(),
                status='Active',
                user_id=user.id,
            )
            db.session.add(employee)
            db.session.commit()
        return user.id, employee.id
