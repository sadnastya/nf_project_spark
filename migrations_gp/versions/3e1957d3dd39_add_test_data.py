"""add test data

Revision ID: 3e1957d3dd39
Revises: 60b3fcc774c5
Create Date: 2024-11-06 20:26:08.355032

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e1957d3dd39'
down_revision: Union[str, None] = '60b3fcc774c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open('database_scripts/test_data_pg.sql', 'r') as f:
        sql = f.read()
    op.execute(sql)


def downgrade() -> None:
    op.execute("TRUNCATE TABLE {}".format(", ".join(op.get_tables())))
