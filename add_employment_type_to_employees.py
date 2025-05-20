"""Migration script to add employment_type column to employees table."""
from app import app, db
from sqlalchemy import text


def add_employment_type_column():
    """Add employment_type column to employees table if it doesn't exist."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('employees')]

        if 'employment_type' not in columns:
            print("Adding employment_type column to employees table...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE employees ADD COLUMN employment_type VARCHAR(20)"))
                conn.commit()
            print("Column added successfully.")
        else:
            print("employment_type column already exists in employees table.")


if __name__ == '__main__':
    add_employment_type_column()
