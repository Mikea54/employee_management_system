"""Service helpers for timesheet operations."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Tuple

from app import db
from models import Employee, TimeEntry, Timesheet
from sqlalchemy import func


class TimesheetService:
    """Utility methods for timesheet management."""

    @staticmethod
    def get_navigation(timesheet: Timesheet, user) -> Tuple[Employee | None, Employee | None]:
        """Return previous and next employees for navigation."""
        prev_employee = None
        next_employee = None

        if user.role.name in ['Admin', 'HR']:
            employees = Employee.query.order_by(Employee.last_name, Employee.first_name).all()
            employee_ids = [e.id for e in employees]
        elif user.employee and user.employee.id == timesheet.employee.manager_id:
            direct_reports = Employee.query.filter_by(manager_id=user.employee.id).order_by(Employee.last_name, Employee.first_name).all()
            employee_ids = [e.id for e in direct_reports]
        else:
            return None, None

        if timesheet.employee_id in employee_ids:
            idx = employee_ids.index(timesheet.employee_id)
            if idx > 0:
                prev_employee = Employee.query.get(employee_ids[idx - 1])
            if idx < len(employee_ids) - 1:
                next_employee = Employee.query.get(employee_ids[idx + 1])

        return prev_employee, next_employee

    @staticmethod
    def update_entries_from_form(timesheet: Timesheet, form: dict) -> None:
        """Update timesheet entries based on submitted form data."""
        start_date = timesheet.pay_period.start_date
        end_date = timesheet.pay_period.end_date
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            hours_raw = form.get(f'hours_{date_str}', '0')
            description = form.get(f'description_{date_str}', '')
            entry = TimeEntry.query.filter_by(timesheet_id=timesheet.id, date=current_date).first()
            try:
                hours_val = float(hours_raw) if hours_raw else 0
            except ValueError:
                hours_val = 0

            if entry:
                entry.hours = hours_val
                entry.description = description
            else:
                if hours_val > 0 or description:
                    entry = TimeEntry(timesheet_id=timesheet.id, date=current_date, hours=hours_val, description=description)
                    db.session.add(entry)

            current_date += timedelta(days=1)

        # Recalculate total hours
        timesheet.total_hours = db.session.query(func.sum(TimeEntry.hours)).filter(TimeEntry.timesheet_id == timesheet.id).scalar() or 0
        db.session.commit()

    @staticmethod
    def submit_timesheet(timesheet: Timesheet) -> None:
        """Mark timesheet as submitted."""
        entry_count = TimeEntry.query.filter_by(timesheet_id=timesheet.id).count()
        if entry_count == 0:
            raise ValueError('Cannot submit an empty timesheet.')
        timesheet.status = 'Submitted'
        timesheet.submitted_at = datetime.now()
        timesheet.total_hours = db.session.query(func.sum(TimeEntry.hours)).filter(TimeEntry.timesheet_id == timesheet.id).scalar() or 0
        db.session.commit()

    @staticmethod
    def approve_timesheet(timesheet: Timesheet, approver_id: int, comments: str = '') -> None:
        """Approve a submitted timesheet."""
        if timesheet.status != 'Submitted':
            raise ValueError('Only submitted timesheets can be approved.')
        timesheet.status = 'Approved'
        timesheet.approved_by = approver_id
        timesheet.approved_at = datetime.now()
        timesheet.comments = comments
        db.session.commit()
