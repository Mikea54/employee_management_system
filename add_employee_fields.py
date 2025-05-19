"""Migration script to add new employee fields."""
from flask import Flask
from app import db
from sqlalchemy import Column, Boolean, String, Date, text

def add_employee_fields():
    """Add new fields to the employees table."""
    # Using raw SQL with SQLAlchemy's text construct
    with db.engine.connect() as conn:
        # Need to check if PostgreSQL supports IF NOT EXISTS for ADD COLUMN
        # If not, we'll check if column exists before adding
        try:
            # Check if columns exist
            for column in ['is_manager', 'level', 'education_level', 'birth_date']:
                result = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='employees' AND column_name='{column}'"))
                if result.fetchone() is None:
                    if column == 'is_manager':
                        conn.execute(text(f"ALTER TABLE employees ADD COLUMN {column} BOOLEAN DEFAULT FALSE"))
                    elif column == 'birth_date':
                        conn.execute(text(f"ALTER TABLE employees ADD COLUMN {column} DATE"))
                    else:
                        conn.execute(text(f"ALTER TABLE employees ADD COLUMN {column} VARCHAR(100)"))
                    print(f"Added column {column} to employees table")
                else:
                    print(f"Column {column} already exists")
            
            # Commit the transaction
            conn.commit()
            print("Successfully added new employee fields")
        except Exception as e:
            print(f"Error adding columns: {e}")
            raise

if __name__ == '__main__':
    # Create a minimal Flask application
    app = Flask(__name__)
    app.config.from_object('config.Config')
    db.init_app(app)
    
    with app.app_context():
        add_employee_fields()