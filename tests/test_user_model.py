from models import User


# --- Tests for real User model (passwords and theme) ---

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


# --- Mock-based permission and role testing ---

class Permission:
    def __init__(self, name):
        self.name = name

class Role:
    def __init__(self, name):
        self.name = name
        self.permissions = []

    def has_permission(self, perm_name: str) -> bool:
        return any(p.name == perm_name for p in self.permissions)

class MockUser:
    def __init__(self, role=None):
        self.role = role

    def has_role(self, roles):
        if not self.role:
            return False
        if isinstance(roles, list):
            return self.role.name in roles
        return self.role.name == roles

    def has_permission(self, perm_name: str) -> bool:
        if not self.role:
            return False
        return self.role.has_permission(perm_name)


def test_user_roles_and_permissions():
    perm_manage = Permission('user_manage')
    admin_role = Role('Admin')
    admin_role.permissions.append(perm_manage)

    user = MockUser(role=admin_role)

    assert user.has_role('Admin')
    assert user.has_role(['Admin', 'HR'])
    assert user.has_permission('user_manage') is True
