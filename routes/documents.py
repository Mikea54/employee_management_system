import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, abort, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError
from app import app, db
from models import Document, Employee, DocumentType
from utils.helpers import role_required, allowed_file, save_document

document_bp = Blueprint('documents', __name__, url_prefix='/documents')

@document_bp.route('/')
@login_required
def index():
    """Main document repository page."""
    # Different view based on role
    if current_user.role.name in ['Admin', 'HR']:
        # Get filter parameters
        employee_id = request.args.get('employee_id', type=int)
        document_type = request.args.get('document_type')
        
        # Base query - only join with Employee, not DocumentType
        query = db.session.query(Document, Employee).join(
            Employee, Document.employee_id == Employee.id
        )
        
        # Apply filters
        if employee_id:
            query = query.filter(Document.employee_id == employee_id)
        
        if document_type:
            query = query.filter(Document.document_type == document_type)
        
        # Get results
        documents = query.order_by(Document.upload_date.desc()).all()
        
        # Get filter options
        employees = Employee.query.filter_by(status='Active').all()
        
        # Get document types from both legacy field and DocumentType model
        legacy_types = db.session.query(Document.document_type).distinct().all()
        legacy_types = [dt[0] for dt in legacy_types if dt[0]]
        
        custom_types = DocumentType.query.filter_by(is_active=True).all()
        custom_type_names = [dt.name for dt in custom_types]
        
        # Combine all document types
        all_document_types = list(set(legacy_types + custom_type_names))
        
        return render_template(
            'documents/repository.html',
            documents=documents,
            employees=employees,
            document_types=all_document_types,
            current_filters={
                'employee_id': employee_id,
                'document_type': document_type
            },
            is_admin=True
        )
    
    elif current_user.role.name == 'Manager' and current_user.employee:
        # Get subordinates
        subordinate_ids = [emp.id for emp in current_user.employee.subordinates]
        
        # Get documents for subordinates - no join with DocumentType needed
        documents = db.session.query(Document, Employee).join(
            Employee, Document.employee_id == Employee.id
        ).filter(
            Document.employee_id.in_(subordinate_ids)
        ).order_by(Document.upload_date.desc()).all()
        
        return render_template(
            'documents/repository.html',
            documents=documents,
            is_admin=False
        )
    
    else:
        # Employee sees their own documents
        if not current_user.employee:
            flash('You do not have an employee record.', 'danger')
            return redirect(url_for('dashboard.index'))
        
        documents = Document.query.filter_by(
            employee_id=current_user.employee.id
        ).order_by(Document.upload_date.desc()).all()
        
        return render_template(
            'documents/repository.html',
            employee_documents=documents,
            is_personal=True
        )

@document_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def upload_document():
    """Upload a new document."""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'document' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['document']
        
        # Check if file was selected
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        # Extract form data
        employee_id = request.form.get('employee_id', type=int)
        title = request.form.get('title')
        document_type = request.form.get('document_type')
        description = request.form.get('description')
        
        # Validate required fields
        if not employee_id or not title or not document_type:
            flash('All fields are required.', 'danger')
            return redirect(request.url)
        
        try:
            # Check if employee exists
            employee = Employee.query.get(employee_id)
            if not employee:
                flash('Invalid employee selected.', 'danger')
                return redirect(request.url)
            
            # Save file
            if file and allowed_file(file.filename):
                filename = save_document(file, app.config['UPLOAD_FOLDER'])
                
                if filename:
                    # We don't need to check document type ID since we don't have that column
                    # Just use the document_type string directly
                    
                    # Create document record - no document_type_id as it's not in the DB
                    new_document = Document(
                        title=title,
                        file_path=filename,
                        document_type=document_type,  # This is the only document type field in DB
                        description=description,
                        employee_id=employee_id,
                        uploaded_by=current_user.id
                    )
                    
                    db.session.add(new_document)
                    db.session.commit()
                    
                    flash('Document uploaded successfully!', 'success')
                    return redirect(url_for('documents.index'))
                else:
                    flash('Error saving file.', 'danger')
            else:
                flash('Invalid file type. Allowed types: PDF, DOC, DOCX, XLS, XLSX, TXT, CSV', 'danger')
                
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'danger')
    
    # Get employees for form
    employees = Employee.query.filter_by(status='Active').order_by(Employee.last_name).all()
    
    # Get active document types from database
    custom_types = DocumentType.query.filter_by(is_active=True).order_by(DocumentType.name).all()
    
    # Get distinct legacy document types from existing documents
    legacy_types = db.session.query(Document.document_type).distinct().all()
    legacy_types = [dt[0] for dt in legacy_types if dt[0]]
    
    # Predefined types for backward compatibility
    predefined_types = ['Contract', 'Certification', 'Performance Review', 'ID Document', 'Other']
    
    return render_template(
        'documents/upload.html',
        employees=employees,
        document_types=legacy_types,
        custom_types=custom_types,
        predefined_types=predefined_types
    )

@document_bp.route('/download/<int:document_id>')
@login_required
def download_document(document_id):
    """Download a document."""
    document = Document.query.get_or_404(document_id)
    
    # Check permissions
    if not current_user.role.name in ['Admin', 'HR']:
        if current_user.role.name == 'Manager' and current_user.employee:
            # Check if document belongs to a subordinate
            subordinate_ids = [emp.id for emp in current_user.employee.subordinates]
            if document.employee_id not in subordinate_ids and document.employee_id != current_user.employee.id:
                flash('You do not have permission to download this document.', 'danger')
                return redirect(url_for('documents.index'))
        elif current_user.employee and document.employee_id != current_user.employee.id:
            flash('You do not have permission to download this document.', 'danger')
            return redirect(url_for('documents.index'))
    
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.file_path)
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=document.file_path.split('_', 2)[-1]  # Use original filename
            )
        else:
            flash('File not found.', 'danger')
            return redirect(url_for('documents.index'))
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'danger')
        return redirect(url_for('documents.index'))

@document_bp.route('/delete/<int:document_id>', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def delete_document(document_id):
    """Delete a document."""
    document = Document.query.get_or_404(document_id)
    
    try:
        # Delete file from filesystem
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete database record
        db.session.delete(document)
        db.session.commit()
        
        flash('Document deleted successfully.', 'success')
    except OSError as e:
        flash(f'Error deleting file: {str(e)}', 'danger')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Database error: {str(e)}', 'danger')
    
    return redirect(url_for('documents.index'))

# Document Type Management Routes
@document_bp.route('/types')
@login_required
@role_required('Admin', 'HR')
def document_types():
    """View and manage document types."""
    types = DocumentType.query.order_by(DocumentType.name).all()
    return render_template('documents/types.html', document_types=types)

@document_bp.route('/types/add', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def add_document_type():
    """Add a new document type."""
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('Document type name is required.', 'danger')
        return redirect(url_for('documents.document_types'))
    
    # Check if type already exists
    existing_type = DocumentType.query.filter(DocumentType.name == name).first()
    if existing_type:
        flash('A document type with this name already exists.', 'danger')
        return redirect(url_for('documents.document_types'))
    
    try:
        new_type = DocumentType(
            name=name,
            description=description,
            created_by=current_user.id
        )
        
        db.session.add(new_type)
        db.session.commit()
        
        flash('Document type added successfully!', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Database error: {str(e)}', 'danger')
    
    return redirect(url_for('documents.document_types'))

@document_bp.route('/types/<int:type_id>/toggle', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def toggle_document_type(type_id):
    """Toggle a document type's active status."""
    doc_type = DocumentType.query.get_or_404(type_id)
    
    try:
        doc_type.is_active = not doc_type.is_active
        db.session.commit()
        
        status = 'activated' if doc_type.is_active else 'deactivated'
        flash(f'Document type {doc_type.name} has been {status}.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Database error: {str(e)}', 'danger')
    
    return redirect(url_for('documents.document_types'))

@document_bp.route('/api/types')
@login_required
def api_document_types():
    """API endpoint to get document types."""
    # Default to active types only
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    query = DocumentType.query
    if active_only:
        query = query.filter_by(is_active=True)
    
    types = query.order_by(DocumentType.name).all()
    
    return jsonify({
        'status': 'success',
        'data': [{'id': t.id, 'name': t.name, 'description': t.description} for t in types]
    })
