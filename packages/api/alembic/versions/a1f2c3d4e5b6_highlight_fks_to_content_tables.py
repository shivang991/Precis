"""highlight FKs to content tables

Revision ID: a1f2c3d4e5b6
Revises: 69ca3547afcf
Create Date: 2026-04-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1f2c3d4e5b6'
down_revision: Union[str, None] = '69ca3547afcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No production data to preserve; drop existing highlight rows so we can
    # safely re-point FKs and add UNIQUE constraints.
    op.execute("DELETE FROM text_highlights")
    op.execute("DELETE FROM table_highlights")
    op.execute("DELETE FROM image_highlights")

    op.drop_constraint(
        "text_highlights_node_id_fkey", "text_highlights", type_="foreignkey"
    )
    op.create_foreign_key(
        "text_highlights_node_id_fkey",
        "text_highlights",
        "text_contents",
        ["node_id"],
        ["node_id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "table_highlights_node_id_fkey", "table_highlights", type_="foreignkey"
    )
    op.create_foreign_key(
        "table_highlights_node_id_fkey",
        "table_highlights",
        "table_contents",
        ["node_id"],
        ["node_id"],
        ondelete="CASCADE",
    )
    op.drop_index("ix_table_highlights_node_id", table_name="table_highlights")
    op.create_index(
        "ix_table_highlights_node_id",
        "table_highlights",
        ["node_id"],
        unique=True,
    )

    op.drop_constraint(
        "image_highlights_node_id_fkey", "image_highlights", type_="foreignkey"
    )
    op.create_foreign_key(
        "image_highlights_node_id_fkey",
        "image_highlights",
        "image_contents",
        ["node_id"],
        ["node_id"],
        ondelete="CASCADE",
    )
    op.drop_index("ix_image_highlights_node_id", table_name="image_highlights")
    op.create_index(
        "ix_image_highlights_node_id",
        "image_highlights",
        ["node_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_image_highlights_node_id", table_name="image_highlights")
    op.create_index(
        "ix_image_highlights_node_id",
        "image_highlights",
        ["node_id"],
        unique=False,
    )
    op.drop_constraint(
        "image_highlights_node_id_fkey", "image_highlights", type_="foreignkey"
    )
    op.create_foreign_key(
        "image_highlights_node_id_fkey",
        "image_highlights",
        "document_nodes",
        ["node_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index("ix_table_highlights_node_id", table_name="table_highlights")
    op.create_index(
        "ix_table_highlights_node_id",
        "table_highlights",
        ["node_id"],
        unique=False,
    )
    op.drop_constraint(
        "table_highlights_node_id_fkey", "table_highlights", type_="foreignkey"
    )
    op.create_foreign_key(
        "table_highlights_node_id_fkey",
        "table_highlights",
        "document_nodes",
        ["node_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "text_highlights_node_id_fkey", "text_highlights", type_="foreignkey"
    )
    op.create_foreign_key(
        "text_highlights_node_id_fkey",
        "text_highlights",
        "document_nodes",
        ["node_id"],
        ["id"],
        ondelete="CASCADE",
    )
