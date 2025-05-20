"""Migration script to add tax_amount column to payrolls table."""
from app import app, db
from sqlalchemy import text

def add_tax_amount_column():
    """Add tax_amount column to payrolls table if it doesn't exist."""
    with app.app_context():
        # Check if the column exists
        inspector = db.inspect(db.engine)
        columns = [column['name'] for column in inspector.get_columns('payrolls')]
        
        if 'tax_amount' not in columns:
            print("Adding tax_amount column to payrolls table...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE payrolls ADD COLUMN tax_amount FLOAT DEFAULT 0.0 NOT NULL'))
                conn.commit()
            print("Column added successfully.")
        else:
            print("tax_amount column already exists in payrolls table.")

if __name__ == '__main__':
    add_tax_amount_column()
