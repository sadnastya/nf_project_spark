"""add test_data

Revision ID: b84067e64c48
Revises: 048a774d28e4
Create Date: 2024-10-31 17:41:43.694371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b84067e64c48'
down_revision: Union[str, None] = '048a774d28e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open('database_scripts/test_data_pg.sql', 'r') as f:
        sql = f.read()
    op.execute(sql)


def downgrade() -> None:
    op.execute("TRUNCATE TABLE {}".format(", ".join(op.get_tables())))
    
