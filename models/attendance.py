from app import db


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    clock_in = db.Column(db.DateTime)
    clock_out = db.Column(db.DateTime)
    status = db.Column(db.String(20))
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<Attendance {self.employee_id} {self.date}>'
