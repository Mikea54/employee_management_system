"""Migration script to add metadata columns to compensation_reports table."""
from app import app, db
from sqlalchemy import text


def add_metadata_columns():
    """Add additional columns used by routes if they don't exist."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing = [c['name'] for c in inspector.get_columns('compensation_reports')]
        columns_to_add = []

        if 'name' not in existing:
            columns_to_add.append('ADD COLUMN name VARCHAR(100)')
        if 'report_type' not in existing:
            columns_to_add.append('ADD COLUMN report_type VARCHAR(20)')
        if 'include_benefits' not in existing:
            columns_to_add.append('ADD COLUMN include_benefits BOOLEAN DEFAULT FALSE')
        if 'include_bonuses' not in existing:
            columns_to_add.append('ADD COLUMN include_bonuses BOOLEAN DEFAULT FALSE')
        if 'department_id' not in existing:
            columns_to_add.append('ADD COLUMN department_id INTEGER')
        if 'updated_at' not in existing:
            columns_to_add.append('ADD COLUMN updated_at DATETIME DEFAULT GETDATE()')
        if columns_to_add:
            with db.engine.connect() as conn:
                for stmt in columns_to_add:
                    conn.execute(text(f'ALTER TABLE compensation_reports {stmt}'))
                conn.commit()
            print('Metadata columns added to compensation_reports.')
        else:
            print('All compensation_reports metadata columns already exist.')


if __name__ == '__main__':
    add_metadata_columns()
