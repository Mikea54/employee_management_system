import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from utils.filters import format_currency, format_date


class Base(DeclarativeBase):
    pass


# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def create_app(config: dict | None = None) -> Flask:
    """Application factory used for tests and production."""
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Load default configuration then apply overrides
    app.config.from_object('config.Config')
    if config:
        app.config.update(config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register custom Jinja2 filters
    app.jinja_env.filters['format_currency'] = format_currency
    app.jinja_env.filters['format_date'] = format_date

    # Import and register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.employees import employee_bp
    from routes.attendance import attendance_bp
    from routes.leave import leave_bp
    from routes.documents import document_bp
    from routes.organization import organization_bp
    from routes.admin import admin_bp
    from routes.timesheets import timesheet_bp
    from routes.payroll import payroll
    from routes.budgeting import budgeting_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(leave_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(organization_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(timesheet_bp, url_prefix='/timesheets')
    app.register_blueprint(payroll, url_prefix='/payroll')
    app.register_blueprint(budgeting_bp, url_prefix='/budgeting')

    # Create database tables and seed data
    with app.app_context():
        import models
        db.create_all()
        from seed_data import create_seed_data
        create_seed_data()

        @login_manager.user_loader
        def load_user(user_id: str):
            return models.User.query.get(int(user_id))

    return app


# Default application instance for scripts
app = create_app()
