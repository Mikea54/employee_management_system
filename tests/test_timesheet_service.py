import os
import datetime
import sqlalchemy
import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'testing'

import app
from app import db
from models import Role, User, Employee, PayPeriod, Timesheet, TimeEntry
from utils.timesheet_service import TimesheetService

@pytest.fixture()
def setup_env():
    app.app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_ENGINE_OPTIONS={
            'connect_args': {'check_same_thread': False},
            'poolclass': sqlalchemy.pool.StaticPool,
        },
    )
    with app.app.app_context():
        db.drop_all()
        db.create_all()
        role = Role(name='Admin')
        db.session.add(role)
        db.session.commit()

        user = User(username='admin', email='admin@example.com', role_id=role.id, is_active=True)
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        emp_a = Employee(employee_id='A', first_name='A', last_name='A', email='a@x.com', hire_date=datetime.date.today(), status='Active')
        emp_b = Employee(employee_id='B', first_name='B', last_name='B', email='b@x.com', hire_date=datetime.date.today(), status='Active')
        emp_c = Employee(employee_id='C', first_name='C', last_name='C', email='c@x.com', hire_date=datetime.date.today(), status='Active')
        db.session.add_all([emp_a, emp_b, emp_c])
        db.session.commit()

        period = PayPeriod(start_date=datetime.date.today(), end_date=datetime.date.today() + datetime.timedelta(days=1), status='Open')
        db.session.add(period)
        db.session.commit()

        timesheet = Timesheet(employee_id=emp_b.id, pay_period_id=period.id)
        db.session.add(timesheet)
        db.session.commit()

        yield user, timesheet, period, emp_a, emp_b, emp_c
        db.session.remove()
        db.drop_all()


def test_navigation_links(setup_env):
    user, timesheet, _, emp_a, emp_b, emp_c = setup_env
    with app.app.app_context():
        prev_emp, next_emp = TimesheetService.get_navigation(timesheet, user)
        assert prev_emp.id == emp_a.id
        assert next_emp.id == emp_c.id


def test_update_entries_and_submit(setup_env):
    user, timesheet, period, *_ = setup_env
    with app.app.app_context():
        form = {
            f"hours_{period.start_date.strftime('%Y-%m-%d')}": '4',
            f"description_{period.start_date.strftime('%Y-%m-%d')}": 'work',
            f"hours_{(period.start_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')}": '5',
            f"description_{(period.start_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')}": 'more',
        }
        TimesheetService.update_entries_from_form(timesheet, form)
        entries = TimeEntry.query.filter_by(timesheet_id=timesheet.id).order_by(TimeEntry.date).all()
        assert len(entries) == 2
        assert timesheet.total_hours == 9

        TimesheetService.submit_timesheet(timesheet)
        assert timesheet.status == 'Submitted'
        assert timesheet.submitted_at is not None


def test_approve_timesheet(setup_env):
    user, timesheet, period, *_ = setup_env
    with app.app.app_context():
        form = {f"hours_{period.start_date.strftime('%Y-%m-%d')}": '1'}
        TimesheetService.update_entries_from_form(timesheet, form)
        TimesheetService.submit_timesheet(timesheet)
        TimesheetService.approve_timesheet(timesheet, user.id, 'ok')
        assert timesheet.status == 'Approved'
        assert timesheet.approved_by == user.id
