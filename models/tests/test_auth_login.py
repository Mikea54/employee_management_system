import os
import pytest
from flask import url_for

# Configure in-memory SQLite before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'testing'

from app import create_app, db
from models import User

app = create_app()


@pytest.fixture()
def client():
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:'
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def create_user(username='tester', password='secret', active=True):
    user = User(username=username, email=f'{username}@example.com', is_active=active)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_login_success_redirects_to_dashboard(client):
    with app.app_context():
        create_user('alice', 'password123')
    response = client.post('/login', data={'username': 'alice', 'password': 'password123'})
    assert response.status_code == 302
    assert response.headers['Location'].endswith(url_for('dashboard.index'))


def test_login_invalid_password_shows_message(client):
    with app.app_context():
        create_user('bob', 'correct')
    response = client.post('/login', data={'username': 'bob', 'password': 'wrong'}, follow_redirects=True)
    assert b'Invalid username or password' in response.data


def test_login_inactive_user_shows_message(client):
    with app.app_context():
        user = create_user('charlie', 'mypassword')
        user.is_active = False
        db.session.commit()
    response = client.post('/login', data={'username': 'charlie', 'password': 'mypassword'}, follow_redirects=True)
    assert b'Your account is inactive' in response.data
