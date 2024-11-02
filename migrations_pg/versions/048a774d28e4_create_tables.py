"""create tables

Revision ID: 048a774d28e4
Revises: 
Create Date: 2024-10-31 17:39:22.796751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '048a774d28e4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open('database_scripts/create_pg.sql', 'r') as f:
        sql = f.read()
    op.execute(sql)


def downgrade() -> None:
    op.drop_all_tables()
