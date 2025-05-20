import pytest
from flask import url_for

from app import db
from models import User




def create_user(app, username='tester', password='secret', active=True):
    with app.app_context():
        user = User(username=username, email=f'{username}@example.com', is_active=active)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user


def test_login_success_redirects_to_dashboard(app, client):
    create_user(app, 'alice', 'password123')
    response = client.post('/login', data={'username': 'alice', 'password': 'password123'})
    assert response.status_code == 302
    assert response.headers['Location'].endswith(url_for('dashboard.index'))


def test_login_invalid_password_shows_message(app, client):
    create_user(app, 'bob', 'correct')
    response = client.post('/login', data={'username': 'bob', 'password': 'wrong'}, follow_redirects=True)
    assert b'Invalid username or password' in response.data


def test_login_inactive_user_shows_message(app, client):
    user = create_user(app, 'charlie', 'mypassword')
    with app.app_context():
        user.is_active = False
        db.session.commit()
    response = client.post('/login', data={'username': 'charlie', 'password': 'mypassword'}, follow_redirects=True)
    assert b'Your account is inactive' in response.data
