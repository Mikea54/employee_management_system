import pytest
from app import db
from models import User, Department, Budget


@pytest.fixture()
def department(app, admin_user):
    with app.app_context():
        dept = Department(name='HR', description='HR')
        db.session.add(dept)
        db.session.commit()
        return dept


def create_budget(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        dept = Department.query.first()
        budget = Budget(year=2025, name='Test Budget', description='desc', department_id=dept.id, total_amount=1000.0, created_by=user.id)
        db.session.add(budget)
        db.session.commit()
        return budget.id


def test_budget_routes_status(app, client, admin_user, department):
    client.post('/login', data={'username': 'admin', 'password': 'password'})
    budget_id = create_budget(app)
    resp = client.get('/budgeting/budgets')
    assert resp.status_code == 200

    resp = client.get('/budgeting/budgets/create')
    assert resp.status_code == 200

    resp = client.get(f'/budgeting/budgets/{budget_id}')
    assert resp.status_code == 200

    resp = client.get(f'/budgeting/budgets/{budget_id}/add-item')
    assert resp.status_code == 200
