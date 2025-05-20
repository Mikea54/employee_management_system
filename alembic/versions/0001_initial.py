"""Initial database schema"""

from alembic import op
import sqlalchemy as sa
from app import db
import models

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create all tables using SQLAlchemy metadata."""
    bind = op.get_bind()
    db.metadata.create_all(bind=bind)


def downgrade():
    """Drop all tables."""
    bind = op.get_bind()
    db.metadata.drop_all(bind=bind)
