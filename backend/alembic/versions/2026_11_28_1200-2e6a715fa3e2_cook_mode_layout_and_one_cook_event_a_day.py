"""cook mode layout and one cook event a day

Adds `users.cook_mode_layout`, the layout cook mode opens in ("step" for one
step per screen, "flow" for every step in one column), "step" for every
existing user. Limits the cooking history to one event per user, recipe and
day: duplicates already stored are folded into the first one logged (the
lowest id), which takes over the note of the first duplicate that has one if
its own is empty, and the rest are deleted before the unique constraint is
added. Downgrade drops the constraint and the column; the deleted duplicates
do not come back.

Revision ID: 2e6a715fa3e2
Revises: c5c96404b555
Create Date: 2026-11-28 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "2e6a715fa3e2"
down_revision: str | None = "c5c96404b555"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SAME_DAY = (
    "{alias}.user_id = cook_events.user_id"
    " AND {alias}.recipe_id = cook_events.recipe_id"
    " AND {alias}.cooked_on = cook_events.cooked_on"
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("cook_mode_layout", sa.String(length=16), server_default="step", nullable=False),
    )

    first_of_day = f"(SELECT MIN(k.id) FROM cook_events k WHERE {SAME_DAY.format(alias='k')})"
    noted = f"FROM cook_events d WHERE {SAME_DAY.format(alias='d')} AND d.note <> ''"
    op.execute(
        sa.text(
            f"UPDATE cook_events SET note = (SELECT d.note {noted} ORDER BY d.id LIMIT 1)"
            f" WHERE note = '' AND id = {first_of_day} AND EXISTS (SELECT 1 {noted})"
        )
    )
    op.execute(sa.text(f"DELETE FROM cook_events WHERE id <> {first_of_day}"))

    with op.batch_alter_table("cook_events") as batch_op:
        batch_op.create_unique_constraint(
            "uq_cook_events_user_recipe_day", ["user_id", "recipe_id", "cooked_on"]
        )


def downgrade() -> None:
    with op.batch_alter_table("cook_events") as batch_op:
        batch_op.drop_constraint("uq_cook_events_user_recipe_day", type_="unique")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("cook_mode_layout")
