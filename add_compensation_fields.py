from app import app, db
from sqlalchemy import text
from models import Dependent


def add_compensation_fields():
    """Add new compensation-related fields and tables"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('employees')]

        with db.engine.connect() as conn:
            if 'healthcare_enrolled' not in columns:
                conn.execute(text('ALTER TABLE employees ADD COLUMN healthcare_enrolled BOOLEAN DEFAULT FALSE'))
            if 'healthcare_enrollment_date' not in columns:
                conn.execute(text('ALTER TABLE employees ADD COLUMN healthcare_enrollment_date DATE'))
            if 'is_401k_enrolled' not in columns:
                conn.execute(text('ALTER TABLE employees ADD COLUMN is_401k_enrolled BOOLEAN DEFAULT FALSE'))
            if 'k401_enrollment_date' not in columns:
                conn.execute(text('ALTER TABLE employees ADD COLUMN k401_enrollment_date DATE'))
            if 'cell_phone_stipend' not in columns:
                conn.execute(text('ALTER TABLE employees ADD COLUMN cell_phone_stipend FLOAT DEFAULT 0.0'))
            conn.commit()

        if 'dependents' not in inspector.get_table_names():
            Dependent.__table__.create(db.engine, checkfirst=True)
        print('Migration completed.')


if __name__ == '__main__':
    add_compensation_fields()
