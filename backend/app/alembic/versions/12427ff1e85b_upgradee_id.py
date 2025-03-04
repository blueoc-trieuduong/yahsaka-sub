"""upgradee id

Revision ID: 12427ff1e85b
Revises: 9d3544f982ec
Create Date: 2025-03-04 13:14:19.549672

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '12427ff1e85b'
down_revision = '9d3544f982ec'
branch_labels = None
depends_on = None



def upgrade():
    op.execute("ALTER TABLE org ALTER COLUMN id SET DEFAULT nextval('org_id_seq');")

def downgrade():
    op.execute("ALTER TABLE org ALTER COLUMN id DROP DEFAULT;")
