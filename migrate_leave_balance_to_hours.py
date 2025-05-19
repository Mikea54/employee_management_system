"""Migration script to convert leave balance from days to hours."""
from app import app, db
from models import LeaveBalance
from sqlalchemy import text

def migrate_leave_balance_to_hours():
    """Convert leave balance from days to hours (1 day = 8 hours)."""
    with app.app_context():
        # 1. Add new columns
        db.session.execute(text('ALTER TABLE leave_balances ADD COLUMN total_hours FLOAT;'))
        db.session.execute(text('ALTER TABLE leave_balances ADD COLUMN used_hours FLOAT;'))
        db.session.execute(text('ALTER TABLE leave_balances ADD COLUMN accrual_rate FLOAT DEFAULT 2.80;'))
        
        # 2. Convert existing data (1 day = 8 hours)
        db.session.execute(text('UPDATE leave_balances SET total_hours = total_days * 8;'))
        db.session.execute(text('UPDATE leave_balances SET used_hours = used_days * 8;'))
        
        # 3. Rename the old columns to mark them as deprecated
        db.session.execute(text('ALTER TABLE leave_balances RENAME COLUMN total_days TO total_days_deprecated;'))
        db.session.execute(text('ALTER TABLE leave_balances RENAME COLUMN used_days TO used_days_deprecated;'))
        
        # Commit changes
        db.session.commit()
        
        # 4. Update the LeaveBalance model - This is already handled in the models.py update
        print("Migration completed successfully.")

if __name__ == '__main__':
    migrate_leave_balance_to_hours()