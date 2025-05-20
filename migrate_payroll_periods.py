"""Migration script to merge PayrollPeriod into PayPeriod."""
from app import app, db
from sqlalchemy import text


def migrate_payroll_periods():
    """Migrate payroll_periods table into pay_periods and update payrolls."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        pay_period_columns = [c['name'] for c in inspector.get_columns('pay_periods')]
        payroll_columns = [c['name'] for c in inspector.get_columns('payrolls')]

        with db.engine.connect() as conn:
            # Add missing columns to pay_periods
            if 'payment_date' not in pay_period_columns:
                conn.execute(text('ALTER TABLE pay_periods ADD COLUMN payment_date DATE'))
            if 'is_thirteenth_month' not in pay_period_columns:
                conn.execute(text('ALTER TABLE pay_periods ADD COLUMN is_thirteenth_month BOOLEAN DEFAULT FALSE'))
            if 'updated_at' not in pay_period_columns:
                conn.execute(text('ALTER TABLE pay_periods ADD COLUMN updated_at TIMESTAMP'))

            # Add pay_period_id column to payrolls if needed
            if 'pay_period_id' not in payroll_columns:
                conn.execute(text('ALTER TABLE payrolls ADD COLUMN pay_period_id INTEGER'))
                conn.execute(text('ALTER TABLE payrolls ADD CONSTRAINT fk_payroll_pay_period FOREIGN KEY (pay_period_id) REFERENCES pay_periods(id)'))

            # Copy data from payroll_periods into pay_periods
            if 'payroll_periods' in inspector.get_table_names():
                conn.execute(text(
                    'INSERT INTO pay_periods (start_date, end_date, payment_date, status, is_thirteenth_month, created_at, updated_at) '
                    'SELECT start_date, end_date, payment_date, status, is_thirteenth_month, created_at, updated_at FROM payroll_periods'))
                # Map payrolls to new periods
                conn.execute(text('UPDATE payrolls SET pay_period_id = payroll_period_id'))
                conn.execute(text('ALTER TABLE payrolls DROP COLUMN payroll_period_id'))
                conn.execute(text('DROP TABLE payroll_periods'))

            conn.commit()
        print('Migration completed successfully.')


if __name__ == '__main__':
    migrate_payroll_periods()
