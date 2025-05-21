"""Add hours_per_week column to employee_compensations"""

from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('employee_compensations', sa.Column('hours_per_week', sa.Float(), nullable=True, server_default='40'))
    op.alter_column('employee_compensations', 'hours_per_week', server_default=None)


def downgrade():
    op.drop_column('employee_compensations', 'hours_per_week')
