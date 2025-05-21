import os
import datetime
import sqlalchemy
import pytest

# Set environment for testing
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'testing-secret'

from app import create_app, db
from models import Employee, PayPeriod, Timesheet, Attendance, TimeEntry
from routes.timesheets import populate_timesheet_from_attendance, calculate_hours_from_attendance

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
            employee_id='EMP001',
            first_name='Test',
            last_name='Employee',
            email='emp@example.com',
            hire_date=datetime.date.today(),
            status='Active'
        )
        db.session.add(employee)
        db.session.commit()

        period = PayPeriod(
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=2),
            status='Open'
        )
        db.session.add(period)
        db.session.commit()

        timesheet = Timesheet(employee_id=employee.id, pay_period_id=period.id)
        db.session.add(timesheet)
        db.session.commit()

        # Add two attendance records
        day1 = period.start_date
        day2 = day1 + datetime.timedelta(days=1)

        att1 = Attendance(
            employee_id=employee.id,
            date=day1,
            clock_in=datetime.datetime.combine(day1, datetime.time(9, 0)),
            clock_out=datetime.datetime.combine(day1, datetime.time(17, 0)),
            status='Present'
        )
        att2 = Attendance(
            employee_id=employee.id,
            date=day2,
            clock_in=datetime.datetime.combine(day2, datetime.time(10, 0)),
            clock_out=datetime.datetime.combine(day2, datetime.time(18, 0)),
            status='Present'
        )
        db.session.add_all([att1, att2])
        db.session.commit()

        yield employee, timesheet, period

        db.session.remove()
        db.drop_all()

def test_populate_timesheet_from_attendance(setup_env):
    employee, timesheet, period = setup_env
    with app.app_context():
        assert TimeEntry.query.count() == 0
        updated = populate_timesheet_from_attendance(timesheet)
        assert updated is True

        entries = TimeEntry.query.filter_by(timesheet_id=timesheet.id).order_by(TimeEntry.date).all()
        assert len(entries) == 2
        assert entries[0].hours == 8.0
        assert entries[1].hours == 8.0
        db.session.refresh(timesheet)
        assert timesheet.total_hours == 16.0

def test_calculate_hours_from_attendance(setup_env):
    employee, *_ = setup_env
    base_date = datetime.date.today()
    with app.app_context():
        # No attendance record
        hours = calculate_hours_from_attendance(employee.id, base_date - datetime.timedelta(days=10))
        assert hours == 0.0

        # Status Present without clock-in/out
        att = Attendance(
            employee_id=employee.id,
            date=base_date + datetime.timedelta(days=3),
            status='Present'
        )
        db.session.add(att)
        db.session.commit()
        hours = calculate_hours_from_attendance(employee.id, att.date)
        assert hours == 8.0

        # Clocked entry with exact times
        att2 = Attendance(
            employee_id=employee.id,
            date=base_date + datetime.timedelta(days=4),
            clock_in=datetime.datetime.combine(base_date, datetime.time(9, 0)),
            clock_out=datetime.datetime.combine(base_date, datetime.time(17, 30))
        )
        db.session.add(att2)
        db.session.commit()
        hours = calculate_hours_from_attendance(employee.id, att2.date)
        assert hours == 8.5
