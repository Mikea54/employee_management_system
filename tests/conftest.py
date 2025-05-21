import os
import sys
import types
import pytest
import sqlalchemy

# Provide a lightweight pandas stub so create_app imports succeed even when
# the real pandas dependency is unavailable in the execution environment.
sys.modules.setdefault(
    "pandas",
    types.SimpleNamespace(read_csv=lambda *a, **k: None, read_excel=lambda *a, **k: None),
)

# Ensure a default in-memory database is used when the app module is imported.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "testing")

from app import create_app, db
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
