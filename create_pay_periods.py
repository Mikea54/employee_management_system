"""
Script to create initial pay periods for the timesheet system.
"""
from datetime import datetime, timedelta
from flask import current_app
from app import db
from models import PayPeriod

def create_initial_pay_periods(start_date_str=None, app=None):
    """Create initial pay periods for the timesheet system.
    
    Args:
        start_date_str: Optional start date in 'YYYY-MM-DD' format.
                      If not provided, will use the first Monday of the current year.
    """
    target_app = app or current_app
    with target_app.app_context():
        # Check if there are existing pay periods
        existing_count = PayPeriod.query.count()
        if existing_count > 0:
            print(f"Found {existing_count} existing pay periods. Deleting them before creating new ones.")
            PayPeriod.query.delete()
            db.session.commit()
        
        # Create pay periods for the current year
        today = datetime.now().date()
        current_year = today.year
        
        # Use provided start date or find the first Monday of the year
        if start_date_str:
            try:
                first_monday = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                print(f"Using provided start date: {first_monday}")
                current_year = first_monday.year
            except ValueError:
                print(f"Invalid date format: {start_date_str}. Using default.")
                # Fall back to default (first Monday of year)
                first_day = datetime(current_year, 1, 1).date()
                days_to_monday = (7 - first_day.weekday()) % 7  # 0 is Monday in Python
                if days_to_monday == 0:  # If it's already Monday
                    first_monday = first_day
                else:
                    first_monday = first_day + timedelta(days=days_to_monday)
        else:
            # Default to first Monday of the current year
            first_day = datetime(current_year, 1, 1).date()
            days_to_monday = (7 - first_day.weekday()) % 7  # 0 is Monday in Python
            if days_to_monday == 0:  # If it's already Monday
                first_monday = first_day
            else:
                first_monday = first_day + timedelta(days=days_to_monday)
        
        # Create pay periods for each two-week period
        start_date = first_monday
        periods_created = 0
        
        while start_date.year <= current_year:
            # End date is 13 days after start date, making a 14-day period in total
            # (start date is day 1, end date is day 14)
            end_date = start_date + timedelta(days=13)  
            
            # Create the pay period
            period = PayPeriod(
                start_date=start_date,
                end_date=end_date,
                status='Open' if start_date <= today and end_date >= today else 'Closed'
            )
            db.session.add(period)
            
            # Move to next period
            start_date = end_date + timedelta(days=1)
            periods_created += 1
            
            # If we've created pay periods up through the current period and 3 future periods, stop
            if start_date > today + timedelta(days=42):  # 3 future pay periods (6 weeks)
                break
        
        db.session.commit()
        print(f"Created {periods_created} pay periods.")
        
        # Show details of the pay periods
        pay_periods = PayPeriod.query.order_by(PayPeriod.start_date).all()
        for period in pay_periods:
            status_str = "CURRENT" if period.is_current else period.status
            print(f"Period {period.id}: {period.start_date} to {period.end_date} - {status_str}")

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    create_initial_pay_periods(app=app)
