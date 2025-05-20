import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from utils.filters import format_currency


class Base(DeclarativeBase):
    pass


# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Load configuration
app.config.from_object('config.Config')

# Initialize SQLAlchemy with app
db.init_app(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Register custom Jinja2 filters
app.jinja_env.filters['format_currency'] = format_currency

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

# Create database tables
with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    import models
    db.create_all()
    from seed_data import create_seed_data
    create_seed_data()
    
    # Set up user loader
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))
