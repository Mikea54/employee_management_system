import os
from urllib.parse import quote_plus

class Config:
    """Configuration class for Flask application."""
    
    # Database settings for Microsoft SQL Server
    DB_SERVER = os.environ.get('MSSQL_HOST', 'localhost')
    DB_PORT = os.environ.get('MSSQL_PORT', '1433')
    DB_NAME = os.environ.get('MSSQL_DATABASE', 'employee_management')
    DB_USER = os.environ.get('MSSQL_USER', 'sa')
    DB_PASSWORD = os.environ.get('MSSQL_PASSWORD', '')

    # Create database URL for MSSQL using pyodbc driver
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or (
        f"mssql+pyodbc://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_SERVER}:{DB_PORT}/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server"
    )
    
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
