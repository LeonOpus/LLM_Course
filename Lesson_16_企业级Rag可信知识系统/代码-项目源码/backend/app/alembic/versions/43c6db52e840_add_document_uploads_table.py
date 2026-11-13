"""Add document_uploads table

Revision ID: 43c6db52e840
Revises: 980b32f130df
Create Date: 2025-06-19 22:39:20.210028

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# generated: lpf2-18Lb8 lpf2-19A32
revision: str = '43c6db52e840'
down_revision: Union[str, None] = '980b32f130df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create document_uploads table
    op.create_table(
        'document_uploads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=16), nullable=False),
        sa.Column('document_name', sa.String(length=255), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('upload_time', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_document_uploads_session_id', 'document_uploads', ['session_id'])
    op.create_index('idx_document_uploads_upload_time', 'document_uploads', ['upload_time'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_document_uploads_upload_time', table_name='document_uploads')
    op.drop_index('idx_document_uploads_session_id', table_name='document_uploads')
    
    # Drop table
    op.drop_table('document_uploads')
