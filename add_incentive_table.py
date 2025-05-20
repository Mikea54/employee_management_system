"""Migration script to add employee_incentives table for bonuses and commissions."""
from app import app, db
from sqlalchemy import text


def add_incentive_table():
    """Create employee_incentives table if it doesn't exist."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        if 'employee_incentives' in inspector.get_table_names():
            print('employee_incentives table already exists.')
            return

        with db.engine.connect() as conn:
            conn.execute(text(
                'CREATE TABLE employee_incentives ('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'employee_id INTEGER NOT NULL, '
                'incentive_type VARCHAR(20) NOT NULL, '
                'amount FLOAT NOT NULL, '
                'date_awarded DATE, '
                'description TEXT, '
                'created_at TIMESTAMP, '
                'updated_at TIMESTAMP, '
                'FOREIGN KEY(employee_id) REFERENCES employees(id)'
                ')' 
            ))
            conn.commit()
        print('employee_incentives table created successfully.')


if __name__ == '__main__':
    add_incentive_table()
