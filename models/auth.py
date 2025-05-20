from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Association table between roles and permissions
role_permissions = db.Table(
    'role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True),
)


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(250))

    users = db.relationship('User', backref='role', lazy='dynamic')
    permissions = db.relationship('Permission', secondary=role_permissions, backref='roles', lazy='dynamic')

    def has_permission(self, perm_name: str) -> bool:
        """Check if role has the specified permission."""
        return any(p.name == perm_name for p in self.permissions)

    def __repr__(self):
        return f'<Role {self.name}>'


class Permission(db.Model):
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Permission {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    theme_preference = db.Column(db.String(20), default='dark')  # 'dark' or 'light'

    # One-to-one relationship with Employee
    employee = db.relationship('Employee', uselist=False, back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_theme(self):
        return self.theme_preference or 'dark'

    def toggle_theme(self):
        if self.theme_preference == 'dark':
            self.theme_preference = 'light'
        else:
            self.theme_preference = 'dark'
        return self.theme_preference

    def has_role(self, roles):
        """Check if user has one of the specified roles"""
        if not self.role:
            return False
        if isinstance(roles, list):
            return self.role.name in roles
        return self.role.name == roles

    def has_permission(self, perm_name: str) -> bool:
        """Check if the user's role includes the given permission."""
        if not self.role:
            return False
        return self.role.has_permission(perm_name)

    def __repr__(self):
        return f'<User {self.username}>'
