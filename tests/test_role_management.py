import os
import sqlalchemy
import pytest

# Configure in-memory database before importing the app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'testing'

import app
from app import db
from models import Role, Permission, User
from seed_data import create_seed_data
from utils import roles as utils_roles
from utils import helpers as utils_helpers

# Add simple routes for decorator testing
@app.app.route('/utils-protected')
@utils_roles.role_required('Admin')
def utils_protected():
    return 'utils protected'

@app.app.route('/helpers-protected')
@utils_helpers.role_required('Admin')
def helpers_protected():
    return 'helpers protected'

@app.app.route('/helpers-multi')
@utils_helpers.role_required('Admin', 'HR')
def helpers_multi():
    return 'helpers multi'

@pytest.fixture()
def client():
    app.app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_ENGINE_OPTIONS={
            'connect_args': {'check_same_thread': False},
            'poolclass': sqlalchemy.pool.StaticPool,
        },
    )
    with app.app.app_context():
        db.engine.dispose()
        db.drop_all()
        db.create_all()
        create_seed_data()
    with app.app.test_client() as client:
        yield client
        with app.app.app_context():
            db.session.remove()
            db.drop_all()

def login(client, username='admin', password='admin123'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)


def create_user(username, role_name):
    with app.app.app_context():
        role = Role.query.filter_by(name=role_name).first()
        user = User(username=username, email=f'{username}@example.com', role_id=role.id, is_active=True)
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
    return user


def test_role_has_permission_and_user_delegates(client):
    with app.app.app_context():
        perm = Permission(name='test_perm', description='Test Permission')
        db.session.add(perm)
        role = Role(name='Tester', description='testing role')
        role.permissions.append(perm)
        db.session.add(role)
        db.session.commit()
        user = User(username='tester', email='tester@example.com', role_id=role.id, is_active=True)
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        assert role.has_permission('test_perm')
        assert user.has_permission('test_perm')
        assert not role.has_permission('missing')
        assert not user.has_permission('missing')


def test_utils_role_required_redirects_and_allows(client):
    # unauthenticated redirect
    resp = client.get('/utils-protected')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']

    # login as non admin
    create_user('emp', 'Employee')
    login(client, 'emp', 'password')
    resp = client.get('/utils-protected')
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/')  # dashboard

    # login as admin
    login(client)
    resp = client.get('/utils-protected')
    assert resp.status_code == 200
    assert b'utils protected' in resp.data


def test_helpers_role_required_behavior(client):
    resp = client.get('/helpers-protected')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']

    create_user('emp2', 'Employee')
    login(client, 'emp2', 'password')
    resp = client.get('/helpers-protected')
    assert resp.status_code == 403

    login(client)
    resp = client.get('/helpers-protected')
    assert resp.status_code == 200

    # multi-role access
    login(client)
    resp = client.get('/helpers-multi')
    assert resp.status_code == 200

    login(client, 'emp2', 'password')
    resp = client.get('/helpers-multi')
    assert resp.status_code == 403


def test_create_role_route(client):
    login(client)
    data = {
        'name': 'MyRole',
        'description': 'desc',
        'permissions[]': ['employee_view', 'employee_edit'],
    }
    client.post('/admin/roles/create', data=data)
    with app.app.app_context():
        role = Role.query.filter_by(name='MyRole').first()
        assert role is not None
        perms = [p.name for p in role.permissions]
        assert 'employee_view' in perms and 'employee_edit' in perms

    # duplicate name
    resp = client.post('/admin/roles/create', data=data, follow_redirects=True)
    assert b'Role name already exists' in resp.data

    # missing name
    resp = client.post('/admin/roles/create', data={'name': ''}, follow_redirects=True)
    assert b'Role name is required' in resp.data


def test_edit_role_route(client):
    login(client)
    with app.app.app_context():
        role = Role(name='TempRole', description='temp')
        db.session.add(role)
        db.session.commit()
        rid = role.id

    data = {
        'name': 'UpdatedRole',
        'description': 'updated',
        'permissions[]': ['employee_view'],
    }
    client.post(f'/admin/roles/edit/{rid}', data=data)
    with app.app.app_context():
        role = Role.query.get(rid)
        assert role.name == 'UpdatedRole'
        assert role.description == 'updated'
        assert role.permissions.count() == 1

    # duplicate name check
    with app.app.app_context():
        other = Role(name='OtherRole')
        db.session.add(other)
        db.session.commit()
    resp = client.post(f'/admin/roles/edit/{rid}', data={'name': 'OtherRole'}, follow_redirects=True)
    assert b'Role name already exists' in resp.data



def test_admin_routes_forbidden_to_non_admin(client):
    create_user('emp3', 'Employee')
    login(client, 'emp3', 'password')
    resp = client.post('/admin/roles/create', data={'name': 'X'})
    assert resp.status_code == 403
    with app.app.app_context():
        role = Role(name='R1')
        db.session.add(role)
        db.session.commit()
        rid = role.id
    resp = client.post(f'/admin/roles/edit/{rid}', data={'name': 'Y'})
    assert resp.status_code == 403


def test_seed_data_idempotent(client):
    with app.app.app_context():
        role_count = Role.query.count()
        perm_count = Permission.query.count()
        create_seed_data()
        assert Role.query.count() == role_count
        assert Permission.query.count() == perm_count

