import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    SECRET_KEY = os.getenv('SESSION_SECRET', 'secret')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
