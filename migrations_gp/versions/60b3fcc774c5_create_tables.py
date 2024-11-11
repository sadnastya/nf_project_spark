"""create tables

Revision ID: 60b3fcc774c5
Revises: 
Create Date: 2024-11-06 20:18:21.997138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60b3fcc774c5'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open('database_scripts/create_gplum.sql', 'r') as f:
        sql = f.read()
    op.execute(sql)


def downgrade() -> None:
    op.drop_all_tables()
