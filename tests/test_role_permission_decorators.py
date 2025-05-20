import pytest
from flask import Flask
from utils.helpers import role_required, permission_required
from flask_login import utils as login_utils
from werkzeug.exceptions import Forbidden


class DummyUser:
    def __init__(self, role_name=None, perms=None, authenticated=True):
        self.is_authenticated = authenticated
        self.role = type('Role', (), {"name": role_name})() if role_name else None
        self._perms = perms or []

    def has_permission(self, perm):
        return perm in self._perms


def test_role_required_allows_access(monkeypatch):
    app = Flask(__name__)

    @role_required('Admin')
    def view():
        return 'ok'

    user = DummyUser('Admin')
    monkeypatch.setattr(login_utils, '_get_user', lambda: user)

    with app.test_request_context('/admin'):
        assert view() == 'ok'


def test_role_required_forbidden(monkeypatch):
    app = Flask(__name__)

    @role_required('Admin')
    def view():
        return 'ok'

    user = DummyUser('User')
    monkeypatch.setattr(login_utils, '_get_user', lambda: user)

    with app.test_request_context('/admin'):
        with pytest.raises(Forbidden):
            view()


def test_permission_required_allows(monkeypatch):
    app = Flask(__name__)

    @permission_required('edit')
    def view():
        return 'ok'

    user = DummyUser('Admin', perms=['edit'])
    monkeypatch.setattr(login_utils, '_get_user', lambda: user)

    with app.test_request_context('/edit'):
        assert view() == 'ok'


def test_permission_required_forbidden(monkeypatch):
    app = Flask(__name__)

    @permission_required('edit')
    def view():
        return 'ok'

    user = DummyUser('Admin', perms=[])
    monkeypatch.setattr(login_utils, '_get_user', lambda: user)

    with app.test_request_context('/edit'):
        with pytest.raises(Forbidden):
            view()
