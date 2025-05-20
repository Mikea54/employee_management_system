import pytest
from datetime import date, timedelta

from app import db
from models import PayPeriod


def login(client, username='admin', password='admin123'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

def test_create_next_period(app, client, admin_user):
    with app.app_context():
        start = date(2024, 1, 1)
        end = start + timedelta(days=13)
        first_period = PayPeriod(start_date=start, end_date=end, status='Open')
        db.session.add(first_period)
        db.session.commit()
        first_end = first_period.end_date

    login(client)
    client.get('/payroll/create-next-period', follow_redirects=True)

    with app.app_context():
        periods = PayPeriod.query.order_by(PayPeriod.start_date).all()
        assert len(periods) == 2
        second = periods[1]
        assert second.start_date == first_end + timedelta(days=1)
        assert second.status == 'Draft'

def test_create_annual_periods(app, client, admin_user):
    login(client)
    client.get('/payroll/create-annual-periods', follow_redirects=True)
    with app.app_context():
        assert PayPeriod.query.count() == 26
