import os
from urllib.parse import quote_plus

class Config:
    """Configuration class for Flask application."""
    
    # Database settings for PostgreSQL
    DB_SERVER = os.environ.get('PGHOST', 'localhost')
    DB_PORT = os.environ.get('PGPORT', '5432')
    DB_NAME = os.environ.get('PGDATABASE', 'employee_management')
    DB_USER = os.environ.get('PGUSER', 'postgres')
    DB_PASSWORD = os.environ.get('PGPASSWORD', '')
    
    # Create database URL for PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"
    
    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Application settings
    DEBUG = True
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
