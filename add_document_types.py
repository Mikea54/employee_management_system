from app import app, db
from models import DocumentType

def create_document_types():
    """Create standard document types"""
    with app.app_context():
        # Check if document types already exist
        if DocumentType.query.count() > 0:
            print("Document types already exist. Skipping.")
            return
            
        print("Creating document types...")
        # Create document types
        contract_type = DocumentType(
            name="Employment Contract",
            description="Official employment contracts and agreements",
            is_active=True
        )
        
        certification_type = DocumentType(
            name="Professional Certification",
            description="Professional qualifications and certifications",
            is_active=True
        )
        
        review_type = DocumentType(
            name="Performance Review",
            description="Employee performance assessments and evaluations",
            is_active=True
        )
        
        id_type = DocumentType(
            name="ID Document",
            description="Identification documents and official credentials",
            is_active=True
        )
        
        tax_type = DocumentType(
            name="Tax Document",
            description="Tax forms and related financial documents",
            is_active=True
        )
        
        db.session.add_all([contract_type, certification_type, review_type, id_type, tax_type])
        db.session.commit()
        print("Document types created successfully.")

if __name__ == "__main__":
    create_document_types()
