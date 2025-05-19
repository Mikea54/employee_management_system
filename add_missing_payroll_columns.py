"""Migration script to add missing columns to payrolls table."""
from app import app, db
from sqlalchemy import text

def add_missing_payroll_columns():
    """Add missing columns to payrolls table if they don't exist."""
    with app.app_context():
        # Check if the columns exist
        inspector = db.inspect(db.engine)
        columns = [column['name'] for column in inspector.get_columns('payrolls')]
        
        with db.engine.connect() as conn:
            # Add created_by column if it doesn't exist
            if 'created_by' not in columns:
                print("Adding created_by column to payrolls table...")
                conn.execute(text('ALTER TABLE payrolls ADD COLUMN created_by INTEGER'))
                # Add foreign key constraint
                conn.execute(text('ALTER TABLE payrolls ADD CONSTRAINT fk_payrolls_created_by FOREIGN KEY (created_by) REFERENCES users(id)'))
                print("Column created_by added successfully.")

            conn.commit()
        
        print("Migration completed successfully.")

if __name__ == '__main__':
    add_missing_payroll_columns()
