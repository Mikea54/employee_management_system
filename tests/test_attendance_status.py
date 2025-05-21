import datetime
import pytest

from models import Attendance, User, Employee
from app import db


def login(client, username, password="password"):
    return client.post('/login', data={'username': username, 'password': password})


def test_status_no_employee(app, client, user_without_employee):
    with app.app_context():
        user = User.query.get(user_without_employee)
    login(client, user.username)
    resp = client.get('/attendance/status')
    assert resp.status_code == 200
    assert resp.get_json() == {
        "clocked_in": False,
        "clocked_out": False,
        "message": "No employee record found",
    }


def test_status_no_record(app, client, user_with_employee):
    user_id, emp_id = user_with_employee
    with app.app_context():
        user = User.query.get(user_id)
    login(client, user.username)
    resp = client.get('/attendance/status')
    assert resp.status_code == 200
    assert resp.get_json() == {
        "clocked_in": False,
        "clocked_out": False,
        "message": "No attendance record for today",
        "can_clock_in_again": True,
    }


def test_status_partial_clock_in(app, client, user_with_employee):
    user_id, employee_id = user_with_employee
    with app.app_context():
        user = User.query.get(user_id)
        employee = Employee.query.get(employee_id)
    clock_in_time = datetime.datetime.combine(datetime.date.today(), datetime.time(8, 0))
    with app.app_context():
        record = Attendance(
            employee_id=employee.id,
            date=datetime.date.today(),
            clock_in=clock_in_time,
            status="Present",
        )
        db.session.add(record)
        db.session.commit()
        expected_clock_in = record.clock_in.isoformat()

    login(client, user.username)
    resp = client.get('/attendance/status')
    assert resp.status_code == 200
    assert resp.get_json() == {
        "clocked_in": True,
        "clocked_out": False,
        "clock_in": expected_clock_in,
        "clock_out": None,
        "status": "Present",
        "multiple_sessions": False,
        "can_clock_in_again": False,
    }


def test_status_completed_session(app, client, user_with_employee):
    user_id, employee_id = user_with_employee
    with app.app_context():
        user = User.query.get(user_id)
        employee = Employee.query.get(employee_id)
    today = datetime.date.today()
    clock_in_time = datetime.datetime.combine(today, datetime.time(8, 0))
    clock_out_time = datetime.datetime.combine(today, datetime.time(16, 0))
    with app.app_context():
        record = Attendance(
            employee_id=employee.id,
            date=today,
            clock_in=clock_in_time,
            clock_out=clock_out_time,
            status="Present",
        )
        db.session.add(record)
        db.session.commit()
        expected_in = record.clock_in.isoformat()
        expected_out = record.clock_out.isoformat()

    login(client, user.username)
    resp = client.get('/attendance/status')
    assert resp.status_code == 200
    assert resp.get_json() == {
        "clocked_in": False,
        "clocked_out": True,
        "clock_in": expected_in,
        "clock_out": expected_out,
        "status": "Present",
        "multiple_sessions": False,
        "can_clock_in_again": True,
    }
