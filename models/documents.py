from datetime import datetime
from app import db


class DocumentType(db.Model):
    __tablename__ = 'document_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', backref='created_document_types')

    def __repr__(self):
        return f'<DocumentType {self.name}>'


class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(50))
    description = db.Column(db.Text)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    uploader = db.relationship('User', backref='uploaded_documents')

    def __repr__(self):
        return f'<Document {self.title}>'
