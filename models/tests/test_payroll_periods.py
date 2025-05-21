import os
import sqlalchemy
import pytest
from datetime import date, timedelta

os.environ['SESSION_SECRET'] = 'testing'

from app import create_app, db
from seed_data import create_seed_data
from models import PayPeriod

app = create_app()

@pytest.fixture()
def client():
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_ENGINE_OPTIONS={
            'connect_args': {'check_same_thread': False},
            'poolclass': sqlalchemy.pool.StaticPool,
        },
    )
    with app.app_context():
        db.engine.dispose()
        db.drop_all()
        db.create_all()
        create_seed_data()
    with app.test_client() as client:
        yield client

def login(client, username='admin', password='admin123'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

def test_create_next_period(client):
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

def test_create_annual_periods(client):
    login(client)
    client.get('/payroll/create-annual-periods', follow_redirects=True)
    with app.app_context():
        assert PayPeriod.query.count() == 26
