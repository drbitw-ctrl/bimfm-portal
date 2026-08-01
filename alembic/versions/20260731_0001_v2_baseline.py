"""BIMFM Portal v2 baseline

Revision ID: 20260731_0001
"""
from alembic import op
from app.database import Base
from app import models  # noqa
revision="20260731_0001"
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    bind=op.get_bind()
    Base.metadata.create_all(bind=bind)
def downgrade():
    pass
