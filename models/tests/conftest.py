import os
import pytest
from app import create_app, db
import sqlalchemy
from models import Role, User

@pytest.fixture()
def app():
    os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
    os.environ.setdefault('SECRET_KEY', 'testing')
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False},
            'poolclass': sqlalchemy.pool.StaticPool,
        },
    })
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
        return user
