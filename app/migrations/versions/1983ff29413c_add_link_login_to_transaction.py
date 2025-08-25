"""add link_login to Transaction

Revision ID: 1983ff29413c
Revises: 
Create Date: 2025-08-25 13:10:00.955939

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1983ff29413c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ustun allaqachon qo‘shilgan, hech narsa qilmaymiz
    pass


def downgrade():
    # rollback uchun ustunni olib tashlaymiz
    op.drop_column('transaction', 'link_login')
