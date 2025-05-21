import os
import datetime
import sqlalchemy
import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'testing'

from app import create_app, db
from models import Employee, Attendance
from routes.timesheets import calculate_hours_from_attendance

app = create_app()


@pytest.fixture()
def setup_env():
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_ENGINE_OPTIONS={
            'connect_args': {'check_same_thread': False},
            'poolclass': sqlalchemy.pool.StaticPool,
        },
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        employee = Employee(
            employee_id='EMP1',
            first_name='Test',
            last_name='User',
            email='emp@example.com',
            hire_date=datetime.date.today(),
            status='Active'
        )
        db.session.add(employee)
        db.session.commit()
        yield employee
        db.session.remove()
        db.drop_all()

def test_calculate_hours_from_attendance(setup_env):
    employee = setup_env
    base_date = datetime.date(2024, 1, 1)
    with app.app_context():
        # No attendance record
        hours = calculate_hours_from_attendance(employee.id, base_date)
        assert hours == 0.0

        # Record with clock times
        clock_date = base_date + datetime.timedelta(days=1)
        att = Attendance(
            employee_id=employee.id,
            date=clock_date,
            clock_in=datetime.datetime.combine(clock_date, datetime.time(9, 0)),
            clock_out=datetime.datetime.combine(clock_date, datetime.time(17, 30))
        )
        db.session.add(att)
        db.session.commit()
        hours = calculate_hours_from_attendance(employee.id, clock_date)
        assert hours == 8.5

        # Status Present without times
        present_date = base_date + datetime.timedelta(days=2)
        att2 = Attendance(
            employee_id=employee.id,
            date=present_date,
            status='Present'
        )
        db.session.add(att2)
        db.session.commit()
        hours = calculate_hours_from_attendance(employee.id, present_date)
        assert hours == 8.0
