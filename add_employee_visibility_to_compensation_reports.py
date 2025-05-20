"""Migration script to add is_visible_to_employee column to compensation_reports table."""
from app import app, db
from sqlalchemy import text


def add_visibility_column():
    """Add is_visible_to_employee column if it doesn't exist."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('compensation_reports')]

        if 'is_visible_to_employee' not in columns:
            print("Adding is_visible_to_employee column to compensation_reports table...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE compensation_reports ADD COLUMN is_visible_to_employee BOOLEAN DEFAULT FALSE"))
                conn.commit()
            print("Column added successfully.")
        else:
            print("is_visible_to_employee column already exists in compensation_reports table.")


if __name__ == '__main__':
    add_visibility_column()
