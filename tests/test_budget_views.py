import os
import sqlalchemy
import pytest

# Configure database before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'testing'

from app import create_app, db
from models import Role, User, Department, Budget


app = create_app()


@pytest.fixture()
def client():
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_ENGINE_OPTIONS={
            'connect_args': {'check_same_thread': False},
            'poolclass': sqlalchemy.pool.StaticPool,
        },
    )
    with app.app_context():
        db.engine.dispose()
        db.drop_all()
        db.create_all()
        admin_role = Role(name='Admin')
        db.session.add(admin_role)
        db.session.commit()
        admin_user = User(username='admin', email='admin@example.com', role_id=admin_role.id, is_active=True)
        admin_user.set_password('password')
        db.session.add(admin_user)
        dept = Department(name='HR', description='HR')
        db.session.add(dept)
        db.session.commit()
    with app.test_client() as client:
        client.post('/login', data={'username': 'admin', 'password': 'password'})
        yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()


def create_budget():
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        dept = Department.query.first()
        budget = Budget(year=2025, name='Test Budget', description='desc', department_id=dept.id, total_amount=1000.0, created_by=user.id)
        db.session.add(budget)
        db.session.commit()
        return budget.id


def test_budget_routes_status(client):
    budget_id = create_budget()
    resp = client.get('/budgeting/budgets')
    assert resp.status_code == 200

    resp = client.get('/budgeting/budgets/create')
    assert resp.status_code == 200

    resp = client.get(f'/budgeting/budgets/{budget_id}')
    assert resp.status_code == 200

    resp = client.get(f'/budgeting/budgets/{budget_id}/add-item')
    assert resp.status_code == 200
