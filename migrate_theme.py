"""Migration script to add theme_preference column to users table."""
import os
from sqlalchemy import create_engine, text
from config import Config

def add_theme_preference_column():
    """Add theme_preference column to users table."""
    # Get database URL from environment or config
    db_url = os.environ.get('DATABASE_URL') or Config.SQLALCHEMY_DATABASE_URI
    
    # Create engine
    engine = create_engine(db_url)
    
    # Execute migration
    with engine.connect() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS theme_preference VARCHAR(20) DEFAULT 'dark'"))
        connection.commit()
        print("Migration successful: Added theme_preference column to users table.")

if __name__ == "__main__":
    add_theme_preference_column()