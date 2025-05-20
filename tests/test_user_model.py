class Permission:
    def __init__(self, name):
        self.name = name

class Role:
    def __init__(self, name):
        self.name = name
        self.permissions = []

    def has_permission(self, perm_name: str) -> bool:
        return any(p.name == perm_name for p in self.permissions)

class User:
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

    user = User(role=admin_role)

    assert user.has_role('Admin')
    assert user.has_role(['Admin', 'HR'])
    assert user.has_permission('user_manage') is True

