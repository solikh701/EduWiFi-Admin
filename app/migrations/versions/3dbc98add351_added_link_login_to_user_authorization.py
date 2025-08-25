from alembic import op
import sqlalchemy as sa

revision = '3dbc98add351'
down_revision = '1983ff29413c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_authorization',
        sa.Column('link_login', sa.String(length=255), nullable=True)
    )


def downgrade():
    op.drop_column('user_authorization', 'link_login')
