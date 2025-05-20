import os

# Configure to use in-memory SQLite DB before importing models
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'testing'

from models import User


def test_password_hashing_and_check():
    user = User(username='test', email='test@example.com')
    user.set_password('secret')
    assert user.password_hash != 'secret'
    assert user.check_password('secret') is True
    assert user.check_password('wrong') is False


def test_toggle_theme_and_get_theme():
    user = User(username='theme', email='theme@example.com')
    # Default should be 'dark'
    assert user.get_theme() == 'dark'
    assert user.toggle_theme() == 'light'
    assert user.get_theme() == 'light'
    assert user.toggle_theme() == 'dark'
    assert user.get_theme() == 'dark'
