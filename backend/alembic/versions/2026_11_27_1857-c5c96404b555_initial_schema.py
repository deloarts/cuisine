"""initial schema

The whole schema of the first release, in one revision. Platform: users with
their avatars, nicknames and display preferences, groups, sessions, trusted
devices, passkeys, personal access tokens, API keys, OAuth clients, grants
and tokens, the security log, the admin settings, legal versions, webhooks
with their deliveries, notices, the file storage and the agent call log of
the MCP surface. Cookbook: units, tags, ingredient categories, families,
aliases and equipment with their translations; ingredients with nutrition,
seasons, conversions and translations; recipes with translations, revisions,
variations, co-editors, shares, steps, step ingredients and step equipment;
households, kitchens, favourites, ratings, notes, food restrictions, cook
events, the meal plan and shared shopping lists; peers, peer invitations,
channels, the inbox, mirrors, incoming recipes and catalogue mappings. The
default units, tags, categories, ingredients and equipment are seeded by the
app on start, not here. Downgrade drops every table.

Revision ID: c5c96404b555
Revises:
Create Date: 2026-11-27 18:57:56.891782

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5c96404b555"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "equipment",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("seed_key", sa.String(length=64), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("icon", sa.String(length=64), nullable=True),
        sa.Column("basic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_equipment")),
        sa.UniqueConstraint("seed_key", name=op.f("uq_equipment_seed_key")),
    )
    op.create_index(op.f("ix_equipment_public_id"), "equipment", ["public_id"], unique=True)
    op.create_table(
        "households",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_households")),
    )
    op.create_index(op.f("ix_households_public_id"), "households", ["public_id"], unique=True)
    op.create_table(
        "ingredient_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("seed_key", sa.String(length=64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingredient_categories")),
        sa.UniqueConstraint("seed_key", name=op.f("uq_ingredient_categories_seed_key")),
    )
    op.create_index(
        op.f("ix_ingredient_categories_public_id"),
        "ingredient_categories",
        ["public_id"],
        unique=True,
    )
    op.create_table(
        "ingredient_families",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("seed_key", sa.String(length=64), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingredient_families")),
        sa.UniqueConstraint("seed_key", name=op.f("uq_ingredient_families_seed_key")),
    )
    op.create_index(
        op.f("ix_ingredient_families_public_id"), "ingredient_families", ["public_id"], unique=True
    )
    op.create_table(
        "oauth_clients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("client_uri", sa.Text(), nullable=True),
        sa.Column(
            "redirect_uris",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("auth_method", sa.String(length=32), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_grant_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauth_clients")),
        sa.UniqueConstraint("client_id", name=op.f("uq_oauth_clients_client_id")),
    )
    op.create_index(op.f("ix_oauth_clients_public_id"), "oauth_clients", ["public_id"], unique=True)
    op.create_table(
        "seeded_keys",
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("seeded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "base",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("kind", "key", name=op.f("pk_seeded_keys")),
    )
    op.create_table(
        "settings",
        sa.Column("section", sa.String(length=32), nullable=False),
        sa.Column(
            "data",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("section", name=op.f("pk_settings")),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("seed_key", sa.String(length=64), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
        sa.UniqueConstraint("seed_key", name=op.f("uq_tags_seed_key")),
    )
    op.create_index(op.f("ix_tags_public_id"), "tags", ["public_id"], unique=True)
    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("seed_key", sa.String(length=64), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("to_base", sa.Float(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_units")),
        sa.UniqueConstraint("code", name=op.f("uq_units_code")),
        sa.UniqueConstraint("seed_key", name=op.f("uq_units_seed_key")),
    )
    op.create_index(op.f("ix_units_public_id"), "units", ["public_id"], unique=True)
    op.create_table(
        "user_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "permissions",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_groups")),
        sa.UniqueConstraint("name", name=op.f("uq_user_groups_name")),
    )
    op.create_index(op.f("ix_user_groups_public_id"), "user_groups", ["public_id"], unique=True)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("full_name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("nickname", sa.String(length=64), nullable=True),
        sa.Column("show_nickname", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("hashed_password", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_systemuser", sa.Boolean(), nullable=False),
        sa.Column("is_service_account", sa.Boolean(), nullable=False),
        sa.Column(
            "permissions",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("theme_preset", sa.String(length=32), nullable=False),
        sa.Column("theme_surface", sa.String(length=32), nullable=False),
        sa.Column("theme_primary", sa.String(length=32), nullable=False),
        sa.Column("theme_dark_mode", sa.Boolean(), nullable=False),
        sa.Column("amount_style", sa.String(length=16), server_default="decimals", nullable=False),
        sa.Column(
            "share_restrictions_with_hosts",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("default_recipe_visibility", sa.String(length=16), nullable=True),
        sa.Column(
            "show_name_on_public_recipes",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "show_name_on_paired_instances",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("recipe_show_tips", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "recipe_show_notes", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "recipe_show_cooked", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "recipe_show_rating", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "recipe_highlight_mentions",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("keep_screen_on", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("avatar_file_id", sa.Integer(), nullable=True),
        sa.Column("privacy_acknowledged_version", sa.Integer(), nullable=True),
        sa.Column("privacy_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_health_data_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_ai_agents_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("last_logged_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("totp_secret", sa.String(length=255), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_public_id"), "users", ["public_id"], unique=True)
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "events",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("secret", sa.String(length=512), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhook_subscriptions")),
    )
    op.create_index(
        op.f("ix_webhook_subscriptions_public_id"),
        "webhook_subscriptions",
        ["public_id"],
        unique=True,
    )
    op.create_table(
        "agent_calls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_kind", sa.String(length=16), nullable=False),
        sa.Column("token_id", sa.Integer(), nullable=False),
        sa.Column("token_name", sa.String(length=128), nullable=False),
        sa.Column("tool", sa.String(length=64), nullable=False),
        sa.Column(
            "arguments",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_refs",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column(
            "result",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("is_draft", sa.Boolean(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_agent_calls_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_calls")),
    )
    op.create_index(op.f("ix_agent_calls_public_id"), "agent_calls", ["public_id"], unique=True)
    op.create_index(
        "ix_agent_calls_token_called_at",
        "agent_calls",
        ["token_kind", "token_id", "called_at"],
        unique=False,
    )
    op.create_index(op.f("ix_agent_calls_user_id"), "agent_calls", ["user_id"], unique=False)
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=32), nullable=False),
        sa.Column("service_user_id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.id"],
            name=op.f("fk_api_keys_creator_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["service_user_id"],
            ["users.id"],
            name=op.f("fk_api_keys_service_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_keys")),
        sa.UniqueConstraint("service_user_id", name=op.f("uq_api_keys_service_user_id")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_api_keys_token_hash")),
    )
    op.create_index(op.f("ix_api_keys_public_id"), "api_keys", ["public_id"], unique=True)
    op.create_table(
        "equipment_aliases",
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("alias", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(
            ["equipment_id"],
            ["equipment.id"],
            name=op.f("fk_equipment_aliases_equipment_id_equipment"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "equipment_id", "locale", "alias", name=op.f("pk_equipment_aliases")
        ),
    )
    op.create_table(
        "equipment_translations",
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(
            ["equipment_id"],
            ["equipment.id"],
            name=op.f("fk_equipment_translations_equipment_id_equipment"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("equipment_id", "locale", name=op.f("pk_equipment_translations")),
    )
    op.create_table(
        "household_invitations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("inviter_id", sa.Integer(), nullable=True),
        sa.Column("invitee_id", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_household_invitations_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invitee_id"],
            ["users.id"],
            name=op.f("fk_household_invitations_invitee_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inviter_id"],
            ["users.id"],
            name=op.f("fk_household_invitations_inviter_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_household_invitations")),
        sa.UniqueConstraint(
            "household_id", "invitee_id", name=op.f("uq_household_invitations_household_id")
        ),
    )
    op.create_index(
        op.f("ix_household_invitations_invitee_id"),
        "household_invitations",
        ["invitee_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_household_invitations_public_id"),
        "household_invitations",
        ["public_id"],
        unique=True,
    )
    op.create_table(
        "household_members",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_household_members_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_household_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_household_members")),
    )
    op.create_index(
        op.f("ix_household_members_household_id"),
        "household_members",
        ["household_id"],
        unique=False,
    )
    op.create_table(
        "ingredient_category_translations",
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["ingredient_categories.id"],
            name=op.f("fk_ingredient_category_translations_category_id_ingredient_categories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "category_id", "locale", name=op.f("pk_ingredient_category_translations")
        ),
    )
    op.create_table(
        "ingredient_family_translations",
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["family_id"],
            ["ingredient_families.id"],
            name=op.f("fk_ingredient_family_translations_family_id_ingredient_families"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "family_id", "locale", name=op.f("pk_ingredient_family_translations")
        ),
    )
    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("seed_key", sa.String(length=64), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("original_locale", sa.String(length=8), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("family_id", sa.Integer(), nullable=True),
        sa.Column("kcal", sa.Float(), nullable=True),
        sa.Column("protein", sa.Float(), nullable=True),
        sa.Column("fat", sa.Float(), nullable=True),
        sa.Column("saturated_fat", sa.Float(), nullable=True),
        sa.Column("carbohydrates", sa.Float(), nullable=True),
        sa.Column("sugar", sa.Float(), nullable=True),
        sa.Column("fibre", sa.Float(), nullable=True),
        sa.Column("salt", sa.Float(), nullable=True),
        sa.Column(
            "extended_nutrition",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "season_months",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("density_g_per_ml", sa.Float(), nullable=True),
        sa.Column(
            "allergens",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "diet_markers",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("nutrition_source", sa.String(length=16), nullable=False),
        sa.Column("usda_fdc_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["ingredient_categories.id"],
            name=op.f("fk_ingredients_category_id_ingredient_categories"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["family_id"],
            ["ingredient_families.id"],
            name=op.f("fk_ingredients_family_id_ingredient_families"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_ingredients_owner_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingredients")),
        sa.UniqueConstraint("seed_key", name=op.f("uq_ingredients_seed_key")),
    )
    op.create_index(op.f("ix_ingredients_family_id"), "ingredients", ["family_id"], unique=False)
    op.create_index(op.f("ix_ingredients_owner_id"), "ingredients", ["owner_id"], unique=False)
    op.create_index(op.f("ix_ingredients_public_id"), "ingredients", ["public_id"], unique=True)
    op.create_table(
        "kitchens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("set_up_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_kitchens_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_kitchens_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kitchens")),
        sa.UniqueConstraint("household_id", name=op.f("uq_kitchens_household_id")),
        sa.UniqueConstraint("user_id", name=op.f("uq_kitchens_user_id")),
    )
    op.create_index(op.f("ix_kitchens_public_id"), "kitchens", ["public_id"], unique=True)
    op.create_table(
        "legal_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "texts",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "privacy_mode",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_by_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["published_by_id"],
            ["users.id"],
            name=op.f("fk_legal_versions_published_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_legal_versions")),
        sa.UniqueConstraint("kind", "version", name="uq_legal_versions_kind_version"),
    )
    op.create_index(
        op.f("ix_legal_versions_public_id"), "legal_versions", ["public_id"], unique=True
    )
    op.create_table(
        "notices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "texts",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_notices_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notices")),
    )
    op.create_index(op.f("ix_notices_public_id"), "notices", ["public_id"], unique=True)
    op.create_table(
        "oauth_grants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column(
            "permissions",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["oauth_clients.id"],
            name=op.f("fk_oauth_grants_client_id_oauth_clients"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_oauth_grants_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauth_grants")),
    )
    op.create_index(op.f("ix_oauth_grants_client_id"), "oauth_grants", ["client_id"], unique=False)
    op.create_index(op.f("ix_oauth_grants_public_id"), "oauth_grants", ["public_id"], unique=True)
    op.create_index(op.f("ix_oauth_grants_user_id"), "oauth_grants", ["user_id"], unique=False)
    op.create_table(
        "passkeys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False),
        sa.Column("backed_up", sa.Boolean(), nullable=False),
        sa.Column(
            "transports",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_passkeys_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_passkeys")),
        sa.UniqueConstraint("credential_id", name=op.f("uq_passkeys_credential_id")),
    )
    op.create_index(op.f("ix_passkeys_public_id"), "passkeys", ["public_id"], unique=True)
    op.create_index(op.f("ix_passkeys_user_id"), "passkeys", ["user_id"], unique=False)
    op.create_table(
        "peers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instance_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("app_version", sa.String(length=64), nullable=False),
        sa.Column("protocol_version", sa.Integer(), nullable=False),
        sa.Column(
            "format_versions",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "capabilities",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("revoked_by", sa.String(length=16), nullable=True),
        sa.Column("inbound_secret", sa.String(length=512), nullable=False),
        sa.Column("outbound_secret", sa.String(length=512), nullable=False),
        sa.Column("users_may_share", sa.Boolean(), nullable=False),
        sa.Column("accept_incoming", sa.Boolean(), nullable=False),
        sa.Column("sync_all", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("mirror_visibility", sa.String(length=16), nullable=False),
        sa.Column("mirror_group_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["mirror_group_id"],
            ["user_groups.id"],
            name=op.f("fk_peers_mirror_group_id_user_groups"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_peers")),
        sa.UniqueConstraint("instance_id", name=op.f("uq_peers_instance_id")),
    )
    op.create_index(op.f("ix_peers_public_id"), "peers", ["public_id"], unique=True)
    op.create_table(
        "personal_access_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=32), nullable=False),
        sa.Column(
            "permissions",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_personal_access_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_personal_access_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_personal_access_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_personal_access_tokens_public_id"),
        "personal_access_tokens",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_personal_access_tokens_user_id"),
        "personal_access_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "detail",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_security_events_actor_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name=op.f("fk_security_events_target_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_security_events")),
    )
    op.create_index(
        op.f("ix_security_events_actor_id"), "security_events", ["actor_id"], unique=False
    )
    op.create_index(
        op.f("ix_security_events_created"), "security_events", ["created"], unique=False
    )
    op.create_index(
        op.f("ix_security_events_event_type"), "security_events", ["event_type"], unique=False
    )
    op.create_index(
        op.f("ix_security_events_public_id"), "security_events", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_security_events_target_user_id"),
        "security_events",
        ["target_user_id"],
        unique=False,
    )
    op.create_table(
        "shopping_list_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("list_name", sa.String(length=128), nullable=False),
        sa.Column("idle_days", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_shopping_list_notes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shopping_list_notes")),
    )
    op.create_index(
        op.f("ix_shopping_list_notes_public_id"), "shopping_list_notes", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_shopping_list_notes_user_id"), "shopping_list_notes", ["user_id"], unique=False
    )
    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mode", sa.String(length=16), server_default="normal", nullable=False),
        sa.Column("keep", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_shopping_lists_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_shopping_lists_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shopping_lists")),
    )
    op.create_index(
        op.f("ix_shopping_lists_household_id"), "shopping_lists", ["household_id"], unique=True
    )
    op.create_index(
        op.f("ix_shopping_lists_owner_id"), "shopping_lists", ["owner_id"], unique=False
    )
    op.create_index(
        op.f("ix_shopping_lists_public_id"), "shopping_lists", ["public_id"], unique=True
    )
    op.create_table(
        "stored_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=127), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("thumbnail_size", sa.Integer(), nullable=True),
        sa.Column("thumbnail_hash", sa.String(length=64), nullable=True),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.id"],
            name=op.f("fk_stored_files_creator_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stored_files")),
    )
    op.create_index(
        op.f("ix_stored_files_creator_id"), "stored_files", ["creator_id"], unique=False
    )
    op.create_index(op.f("ix_stored_files_public_id"), "stored_files", ["public_id"], unique=True)
    op.create_table(
        "tag_translations",
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("fk_tag_translations_tag_id_tags"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tag_id", "locale", name=op.f("pk_tag_translations")),
    )
    op.create_table(
        "trusted_devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_trusted_devices_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trusted_devices")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_trusted_devices_token_hash")),
    )
    op.create_index(
        op.f("ix_trusted_devices_public_id"), "trusted_devices", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_trusted_devices_user_id"), "trusted_devices", ["user_id"], unique=False
    )
    op.create_table(
        "unit_translations",
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("plural_name", sa.String(length=64), nullable=False),
        sa.Column("abbreviation", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["units.id"],
            name=op.f("fk_unit_translations_unit_id_units"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("unit_id", "locale", name=op.f("pk_unit_translations")),
    )
    op.create_table(
        "user_group_members",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["user_groups.id"],
            name=op.f("fk_user_group_members_group_id_user_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_group_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "group_id", name=op.f("pk_user_group_members")),
    )
    op.create_index(
        op.f("ix_user_group_members_group_id"), "user_group_members", ["group_id"], unique=False
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_sessions")),
    )
    op.create_index(op.f("ix_user_sessions_public_id"), "user_sessions", ["public_id"], unique=True)
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subject_user_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subject_user_id"],
            ["users.id"],
            name=op.f("fk_webhook_deliveries_subject_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["webhook_subscriptions.id"],
            name=op.f("fk_webhook_deliveries_subscription_id_webhook_subscriptions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhook_deliveries")),
    )
    op.create_index(
        op.f("ix_webhook_deliveries_public_id"), "webhook_deliveries", ["public_id"], unique=True
    )
    op.create_index(
        "ix_webhook_deliveries_status_next",
        "webhook_deliveries",
        ["status", "next_attempt_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_deliveries_subject_user_id"),
        "webhook_deliveries",
        ["subject_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_webhook_deliveries_subscription_created",
        "webhook_deliveries",
        ["subscription_id", "created"],
        unique=False,
    )
    op.create_table(
        "food_restrictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("allergen", sa.String(length=32), nullable=True),
        sa.Column("diet", sa.String(length=32), nullable=True),
        sa.Column("family_id", sa.Integer(), nullable=True),
        sa.Column("ingredient_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["family_id"],
            ["ingredient_families.id"],
            name=op.f("fk_food_restrictions_family_id_ingredient_families"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredients.id"],
            name=op.f("fk_food_restrictions_ingredient_id_ingredients"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_food_restrictions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_food_restrictions")),
    )
    op.create_index(
        op.f("ix_food_restrictions_public_id"), "food_restrictions", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_food_restrictions_user_id"), "food_restrictions", ["user_id"], unique=False
    )
    op.create_table(
        "ingredient_aliases",
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("alias", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredients.id"],
            name=op.f("fk_ingredient_aliases_ingredient_id_ingredients"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "ingredient_id", "locale", "alias", name=op.f("pk_ingredient_aliases")
        ),
    )
    op.create_table(
        "ingredient_conversions",
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("grams", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredients.id"],
            name=op.f("fk_ingredient_conversions_ingredient_id_ingredients"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["units.id"],
            name=op.f("fk_ingredient_conversions_unit_id_units"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("ingredient_id", "unit_id", name=op.f("pk_ingredient_conversions")),
    )
    op.create_table(
        "ingredient_translations",
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("plural_name", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredients.id"],
            name=op.f("fk_ingredient_translations_ingredient_id_ingredients"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("ingredient_id", "locale", name=op.f("pk_ingredient_translations")),
    )
    op.create_table(
        "kitchen_equipment",
        sa.Column("kitchen_id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["equipment_id"],
            ["equipment.id"],
            name=op.f("fk_kitchen_equipment_equipment_id_equipment"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["kitchen_id"],
            ["kitchens.id"],
            name=op.f("fk_kitchen_equipment_kitchen_id_kitchens"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("kitchen_id", "equipment_id", name=op.f("pk_kitchen_equipment")),
    )
    op.create_index(
        op.f("ix_kitchen_equipment_equipment_id"),
        "kitchen_equipment",
        ["equipment_id"],
        unique=False,
    )
    op.create_table(
        "notice_acknowledgements",
        sa.Column("notice_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["notice_id"],
            ["notices.id"],
            name=op.f("fk_notice_acknowledgements_notice_id_notices"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notice_acknowledgements_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("notice_id", "user_id", name=op.f("pk_notice_acknowledgements")),
    )
    op.create_index(
        op.f("ix_notice_acknowledgements_user_id"),
        "notice_acknowledgements",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "oauth_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("grant_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["grant_id"],
            ["oauth_grants.id"],
            name=op.f("fk_oauth_tokens_grant_id_oauth_grants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauth_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_oauth_tokens_token_hash")),
    )
    op.create_index(op.f("ix_oauth_tokens_grant_id"), "oauth_tokens", ["grant_id"], unique=False)
    op.create_index(op.f("ix_oauth_tokens_public_id"), "oauth_tokens", ["public_id"], unique=True)
    op.create_table(
        "peer_catalogue_mappings",
        sa.Column("peer_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("remote_public_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=True),
        sa.Column("ingredient_id", sa.Integer(), nullable=True),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("tag_id", sa.Integer(), nullable=True),
        sa.Column("equipment_id", sa.Integer(), nullable=True),
        sa.Column("created_here", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("matched_by", sa.String(length=16), nullable=True),
        sa.Column("remote_name", sa.String(length=255), nullable=False),
        sa.Column(
            "remote_data",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["equipment_id"],
            ["equipment.id"],
            name=op.f("fk_peer_catalogue_mappings_equipment_id_equipment"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredients.id"],
            name=op.f("fk_peer_catalogue_mappings_ingredient_id_ingredients"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["peer_id"],
            ["peers.id"],
            name=op.f("fk_peer_catalogue_mappings_peer_id_peers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("fk_peer_catalogue_mappings_tag_id_tags"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["units.id"],
            name=op.f("fk_peer_catalogue_mappings_unit_id_units"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "peer_id", "kind", "remote_public_id", name=op.f("pk_peer_catalogue_mappings")
        ),
    )
    op.create_index(
        op.f("ix_peer_catalogue_mappings_equipment_id"),
        "peer_catalogue_mappings",
        ["equipment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peer_catalogue_mappings_ingredient_id"),
        "peer_catalogue_mappings",
        ["ingredient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peer_catalogue_mappings_tag_id"),
        "peer_catalogue_mappings",
        ["tag_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peer_catalogue_mappings_unit_id"),
        "peer_catalogue_mappings",
        ["unit_id"],
        unique=False,
    )
    op.create_table(
        "peer_channel_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("peer_id", sa.Integer(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("item_id", sa.String(length=128), nullable=False),
        sa.Column("revision", sa.String(length=128), nullable=True),
        sa.Column(
            "data",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["peer_id"],
            ["peers.id"],
            name=op.f("fk_peer_channel_events_peer_id_peers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_peer_channel_events")),
        sa.UniqueConstraint("peer_id", "kind", "item_id", name="uq_peer_channel_events_item"),
    )
    op.create_index(
        "ix_peer_channel_events_peer_seq", "peer_channel_events", ["peer_id", "seq"], unique=False
    )
    op.create_index(
        op.f("ix_peer_channel_events_public_id"), "peer_channel_events", ["public_id"], unique=True
    )
    op.create_table(
        "peer_channels",
        sa.Column("peer_id", sa.Integer(), nullable=False),
        sa.Column("paired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("out_seq", sa.Integer(), nullable=False),
        sa.Column("delivered_seq", sa.Integer(), nullable=False),
        sa.Column("send_attempts", sa.Integer(), nullable=False),
        sa.Column("next_send_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_delivery_status", sa.Integer(), nullable=True),
        sa.Column("last_delivery_error", sa.String(length=64), nullable=True),
        sa.Column("in_seq", sa.Integer(), nullable=False),
        sa.Column("last_catch_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reconcile_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_receive_error", sa.String(length=64), nullable=True),
        sa.Column("catch_up_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconcile_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ping_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("send_lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("receive_lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["peer_id"],
            ["peers.id"],
            name=op.f("fk_peer_channels_peer_id_peers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("peer_id", name=op.f("pk_peer_channels")),
    )
    op.create_table(
        "peer_inbox",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("peer_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=True),
        sa.Column("item_id", sa.String(length=128), nullable=True),
        sa.Column("revision", sa.String(length=128), nullable=True),
        sa.Column("seq", sa.Integer(), nullable=True),
        sa.Column("prev_seq", sa.Integer(), nullable=True),
        sa.Column(
            "data",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["peer_id"], ["peers.id"], name=op.f("fk_peer_inbox_peer_id_peers"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_peer_inbox")),
    )
    op.create_index(
        "ix_peer_inbox_peer_next", "peer_inbox", ["peer_id", "next_attempt_at"], unique=False
    )
    op.create_index(op.f("ix_peer_inbox_public_id"), "peer_inbox", ["public_id"], unique=True)
    op.create_table(
        "peer_incoming_recipes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("peer_id", sa.Integer(), nullable=False),
        sa.Column("origin_public_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("etag", sa.String(length=160), nullable=False),
        sa.Column("payload", sa.LargeBinary(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["peer_id"],
            ["peers.id"],
            name=op.f("fk_peer_incoming_recipes_peer_id_peers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_peer_incoming_recipes")),
        sa.UniqueConstraint("peer_id", "origin_public_id", name="uq_peer_incoming_recipes_origin"),
    )
    op.create_index(
        op.f("ix_peer_incoming_recipes_peer_id"), "peer_incoming_recipes", ["peer_id"], unique=False
    )
    op.create_index(
        op.f("ix_peer_incoming_recipes_public_id"),
        "peer_incoming_recipes",
        ["public_id"],
        unique=True,
    )
    op.create_table(
        "peer_invitations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("peer_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_peer_invitations_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["peer_id"],
            ["peers.id"],
            name=op.f("fk_peer_invitations_peer_id_peers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_peer_invitations")),
        sa.UniqueConstraint("code_hash", name=op.f("uq_peer_invitations_code_hash")),
    )
    op.create_index(
        op.f("ix_peer_invitations_expires_at"), "peer_invitations", ["expires_at"], unique=False
    )
    op.create_index(
        op.f("ix_peer_invitations_public_id"), "peer_invitations", ["public_id"], unique=True
    )
    op.create_table(
        "peer_suggestion_dismissals",
        sa.Column("peer_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("remote_public_id", sa.String(length=64), nullable=False),
        sa.Column("field", sa.String(length=64), nullable=False),
        sa.Column("value_hash", sa.String(length=64), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["peer_id"],
            ["peers.id"],
            name=op.f("fk_peer_suggestion_dismissals_peer_id_peers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "peer_id",
            "kind",
            "remote_public_id",
            "field",
            name=op.f("pk_peer_suggestion_dismissals"),
        ),
    )
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("visibility", sa.String(length=16), server_default="instance", nullable=False),
        sa.Column("original_locale", sa.String(length=8), nullable=False),
        sa.Column("base_servings", sa.Integer(), nullable=False),
        sa.Column("prep_minutes", sa.Integer(), nullable=True),
        sa.Column("cook_minutes", sa.Integer(), nullable=True),
        sa.Column("rest_minutes", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("cover_file_id", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("created_via", sa.String(length=16), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("yield_amount", sa.Float(), nullable=True),
        sa.Column("yield_unit_id", sa.Integer(), nullable=True),
        sa.Column("based_on_recipe_id", sa.Integer(), nullable=True),
        sa.Column("origin_instance_id", sa.Uuid(), nullable=True),
        sa.Column("origin_public_id", sa.Uuid(), nullable=True),
        sa.Column("mirror_peer_id", sa.Integer(), nullable=True),
        sa.Column("peer_capped", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "(origin_instance_id IS NULL) = (origin_public_id IS NULL)",
            name=op.f("ck_recipes_origin_pair"),
        ),
        sa.ForeignKeyConstraint(
            ["based_on_recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipes_based_on_recipe_id_recipes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cover_file_id"],
            ["stored_files.id"],
            name=op.f("fk_recipes_cover_file_id_stored_files"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["mirror_peer_id"],
            ["peers.id"],
            name=op.f("fk_recipes_mirror_peer_id_peers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_recipes_owner_id_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["yield_unit_id"],
            ["units.id"],
            name=op.f("fk_recipes_yield_unit_id_units"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipes")),
        sa.UniqueConstraint(
            "owner_id", "origin_instance_id", "origin_public_id", name="uq_recipes_origin"
        ),
    )
    op.create_index(
        op.f("ix_recipes_based_on_recipe_id"), "recipes", ["based_on_recipe_id"], unique=False
    )
    op.create_index(op.f("ix_recipes_mirror_peer_id"), "recipes", ["mirror_peer_id"], unique=False)
    op.create_index(op.f("ix_recipes_owner_id"), "recipes", ["owner_id"], unique=False)
    op.create_index(op.f("ix_recipes_public_id"), "recipes", ["public_id"], unique=True)
    op.create_index(op.f("ix_recipes_status"), "recipes", ["status"], unique=False)
    op.create_table(
        "shopping_list_members",
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["list_id"],
            ["shopping_lists.id"],
            name=op.f("fk_shopping_list_members_list_id_shopping_lists"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_shopping_list_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("list_id", "user_id", name=op.f("pk_shopping_list_members")),
    )
    op.create_index(
        op.f("ix_shopping_list_members_user_id"), "shopping_list_members", ["user_id"], unique=False
    )
    op.create_table(
        "stored_file_contents",
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("variant", sa.String(length=16), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["stored_files.id"],
            name=op.f("fk_stored_file_contents_file_id_stored_files"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("file_id", "variant", name=op.f("pk_stored_file_contents")),
    )
    op.create_table(
        "meal_plan_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("slot", sa.String(length=16), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("servings", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name=op.f("fk_meal_plan_entries_household_id_households"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_meal_plan_entries_recipe_id_recipes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_meal_plan_entries_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meal_plan_entries")),
    )
    op.create_index(
        op.f("ix_meal_plan_entries_household_id"),
        "meal_plan_entries",
        ["household_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_meal_plan_entries_public_id"), "meal_plan_entries", ["public_id"], unique=True
    )
    op.create_index(
        "ix_meal_plan_entries_user_date",
        "meal_plan_entries",
        ["user_id", "plan_date"],
        unique=False,
    )
    op.create_table(
        "recipe_co_editors",
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_co_editors_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recipe_co_editors_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("recipe_id", "user_id", name=op.f("pk_recipe_co_editors")),
    )
    op.create_index(
        op.f("ix_recipe_co_editors_user_id"), "recipe_co_editors", ["user_id"], unique=False
    )
    op.create_table(
        "recipe_favourites",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_favourites_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recipe_favourites_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "recipe_id", name=op.f("pk_recipe_favourites")),
    )
    op.create_index(
        op.f("ix_recipe_favourites_recipe_id"), "recipe_favourites", ["recipe_id"], unique=False
    )
    op.create_table(
        "recipe_group_shares",
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["user_groups.id"],
            name=op.f("fk_recipe_group_shares_group_id_user_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_group_shares_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("recipe_id", "group_id", name=op.f("pk_recipe_group_shares")),
    )
    op.create_index(
        op.f("ix_recipe_group_shares_group_id"), "recipe_group_shares", ["group_id"], unique=False
    )
    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=True),
        sa.Column("sub_recipe_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredients.id"],
            name=op.f("fk_recipe_ingredients_ingredient_id_ingredients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_ingredients_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sub_recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_ingredients_sub_recipe_id_recipes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["units.id"],
            name=op.f("fk_recipe_ingredients_unit_id_units"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipe_ingredients")),
    )
    op.create_index(
        op.f("ix_recipe_ingredients_ingredient_id"),
        "recipe_ingredients",
        ["ingredient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recipe_ingredients_public_id"), "recipe_ingredients", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_recipe_ingredients_recipe_id"), "recipe_ingredients", ["recipe_id"], unique=False
    )
    op.create_index(
        op.f("ix_recipe_ingredients_sub_recipe_id"),
        "recipe_ingredients",
        ["sub_recipe_id"],
        unique=False,
    )
    op.create_table(
        "recipe_mirrors",
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("peer_id", sa.Integer(), nullable=False),
        sa.Column("origin_public_id", sa.Uuid(), nullable=False),
        sa.Column("etag", sa.String(length=160), nullable=False),
        sa.Column("source_revision", sa.String(length=160), nullable=False),
        sa.Column("source_author_name", sa.String(length=255), nullable=True),
        sa.Column(
            "document",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "files",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "extras",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["peer_id"],
            ["peers.id"],
            name=op.f("fk_recipe_mirrors_peer_id_peers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_mirrors_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("recipe_id", name=op.f("pk_recipe_mirrors")),
        sa.UniqueConstraint("peer_id", "origin_public_id", name="uq_recipe_mirrors_origin"),
    )
    op.create_index(op.f("ix_recipe_mirrors_peer_id"), "recipe_mirrors", ["peer_id"], unique=False)
    op.create_table(
        "recipe_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_notes_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recipe_notes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipe_notes")),
        sa.UniqueConstraint("user_id", "recipe_id", name=op.f("uq_recipe_notes_user_id")),
    )
    op.create_index(op.f("ix_recipe_notes_public_id"), "recipe_notes", ["public_id"], unique=True)
    op.create_index("ix_recipe_notes_recipe_id", "recipe_notes", ["recipe_id"], unique=False)
    op.create_table(
        "recipe_peer_shares",
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("peer_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["peer_id"],
            ["peers.id"],
            name=op.f("fk_recipe_peer_shares_peer_id_peers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_peer_shares_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("recipe_id", "peer_id", name=op.f("pk_recipe_peer_shares")),
    )
    op.create_index(
        op.f("ix_recipe_peer_shares_peer_id"), "recipe_peer_shares", ["peer_id"], unique=False
    )
    op.create_table(
        "recipe_revisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column(
            "snapshot",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("created_via", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("restored_from", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("credited_author_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_recipe_revisions_author_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["credited_author_id"],
            ["users.id"],
            name=op.f("fk_recipe_revisions_credited_author_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_revisions_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipe_revisions")),
        sa.UniqueConstraint("recipe_id", "number", name=op.f("uq_recipe_revisions_recipe_id")),
    )
    op.create_index(
        op.f("ix_recipe_revisions_author_id"), "recipe_revisions", ["author_id"], unique=False
    )
    op.create_index(
        op.f("ix_recipe_revisions_created"), "recipe_revisions", ["created"], unique=False
    )
    op.create_index(
        op.f("ix_recipe_revisions_public_id"), "recipe_revisions", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_recipe_revisions_recipe_id"), "recipe_revisions", ["recipe_id"], unique=False
    )
    op.create_table(
        "recipe_steps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("image_file_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["image_file_id"],
            ["stored_files.id"],
            name=op.f("fk_recipe_steps_image_file_id_stored_files"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_steps_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipe_steps")),
    )
    op.create_index(op.f("ix_recipe_steps_public_id"), "recipe_steps", ["public_id"], unique=True)
    op.create_index(op.f("ix_recipe_steps_recipe_id"), "recipe_steps", ["recipe_id"], unique=False)
    op.create_table(
        "recipe_tags",
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_tags_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"], name=op.f("fk_recipe_tags_tag_id_tags"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("recipe_id", "tag_id", name=op.f("pk_recipe_tags")),
    )
    op.create_index(op.f("ix_recipe_tags_tag_id"), "recipe_tags", ["tag_id"], unique=False)
    op.create_table(
        "recipe_translations",
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tips", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_translations_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("recipe_id", "locale", name=op.f("pk_recipe_translations")),
    )
    op.create_table(
        "recipe_user_shares",
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_user_shares_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recipe_user_shares_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("recipe_id", "user_id", name=op.f("pk_recipe_user_shares")),
    )
    op.create_index(
        op.f("ix_recipe_user_shares_user_id"), "recipe_user_shares", ["user_id"], unique=False
    )
    op.create_table(
        "recipe_variations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("private", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("based_on_revision", sa.Integer(), nullable=True),
        sa.Column(
            "changes",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origin_public_id", sa.Uuid(), nullable=True),
        sa.Column("source_author_name", sa.String(length=255), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_recipe_variations_author_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_variations_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipe_variations")),
    )
    op.create_index(
        op.f("ix_recipe_variations_author_id"), "recipe_variations", ["author_id"], unique=False
    )
    op.create_index(
        op.f("ix_recipe_variations_public_id"), "recipe_variations", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_recipe_variations_recipe_id"), "recipe_variations", ["recipe_id"], unique=False
    )
    op.create_table(
        "shopping_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("checked", sa.Boolean(), nullable=False),
        sa.Column("checked_by_id", sa.Integer(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recipe_id", sa.Integer(), nullable=True),
        sa.Column(
            "extra_recipe_ids",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "sub_recipe_path",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["ingredient_categories.id"],
            name=op.f("fk_shopping_items_category_id_ingredient_categories"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["checked_by_id"],
            ["users.id"],
            name=op.f("fk_shopping_items_checked_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_shopping_items_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredients.id"],
            name=op.f("fk_shopping_items_ingredient_id_ingredients"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["list_id"],
            ["shopping_lists.id"],
            name=op.f("fk_shopping_items_list_id_shopping_lists"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_shopping_items_recipe_id_recipes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["units.id"],
            name=op.f("fk_shopping_items_unit_id_units"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shopping_items")),
    )
    op.create_index(op.f("ix_shopping_items_list_id"), "shopping_items", ["list_id"], unique=False)
    op.create_index(
        op.f("ix_shopping_items_public_id"), "shopping_items", ["public_id"], unique=True
    )
    op.create_table(
        "cook_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("cooked_on", sa.Date(), nullable=False),
        sa.Column("servings", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("variation_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_cook_events_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_cook_events_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["variation_id"],
            ["recipe_variations.id"],
            name=op.f("fk_cook_events_variation_id_recipe_variations"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cook_events")),
    )
    op.create_index(op.f("ix_cook_events_cooked_on"), "cook_events", ["cooked_on"], unique=False)
    op.create_index(op.f("ix_cook_events_public_id"), "cook_events", ["public_id"], unique=True)
    op.create_index(op.f("ix_cook_events_recipe_id"), "cook_events", ["recipe_id"], unique=False)
    op.create_index(op.f("ix_cook_events_user_id"), "cook_events", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_cook_events_variation_id"), "cook_events", ["variation_id"], unique=False
    )
    op.create_table(
        "recipe_ingredient_translations",
        sa.Column("recipe_ingredient_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["recipe_ingredient_id"],
            ["recipe_ingredients.id"],
            name=op.f("fk_recipe_ingredient_translations_recipe_ingredient_id_recipe_ingredients"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "recipe_ingredient_id", "locale", name=op.f("pk_recipe_ingredient_translations")
        ),
    )
    op.create_table(
        "recipe_ratings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("variation_id", sa.Integer(), nullable=True),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name=op.f("fk_recipe_ratings_recipe_id_recipes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recipe_ratings_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["variation_id"],
            ["recipe_variations.id"],
            name=op.f("fk_recipe_ratings_variation_id_recipe_variations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipe_ratings")),
        sa.UniqueConstraint("user_id", "variation_id", name=op.f("uq_recipe_ratings_user_id")),
    )
    op.create_index(
        op.f("ix_recipe_ratings_public_id"), "recipe_ratings", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_recipe_ratings_recipe_id"), "recipe_ratings", ["recipe_id"], unique=False
    )
    op.create_index(
        op.f("ix_recipe_ratings_variation_id"), "recipe_ratings", ["variation_id"], unique=False
    )
    op.create_index(
        "uq_recipe_ratings_user_id_recipe_id_original",
        "recipe_ratings",
        ["user_id", "recipe_id"],
        unique=True,
        postgresql_where=sa.text("variation_id IS NULL"),
        sqlite_where=sa.text("variation_id IS NULL"),
    )
    op.create_table(
        "recipe_step_translations",
        sa.Column("step_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["step_id"],
            ["recipe_steps.id"],
            name=op.f("fk_recipe_step_translations_step_id_recipe_steps"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("step_id", "locale", name=op.f("pk_recipe_step_translations")),
    )
    op.create_table(
        "step_equipment",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("step_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["equipment_id"],
            ["equipment.id"],
            name=op.f("fk_step_equipment_equipment_id_equipment"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["step_id"],
            ["recipe_steps.id"],
            name=op.f("fk_step_equipment_step_id_recipe_steps"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_step_equipment")),
    )
    op.create_index(
        op.f("ix_step_equipment_equipment_id"), "step_equipment", ["equipment_id"], unique=False
    )
    op.create_index(
        op.f("ix_step_equipment_public_id"), "step_equipment", ["public_id"], unique=True
    )
    op.create_index(op.f("ix_step_equipment_step_id"), "step_equipment", ["step_id"], unique=False)
    op.create_table(
        "step_ingredients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("step_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=True),
        sa.Column("sub_recipe_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredients.id"],
            name=op.f("fk_step_ingredients_ingredient_id_ingredients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["step_id"],
            ["recipe_steps.id"],
            name=op.f("fk_step_ingredients_step_id_recipe_steps"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sub_recipe_id"],
            ["recipes.id"],
            name=op.f("fk_step_ingredients_sub_recipe_id_recipes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["units.id"],
            name=op.f("fk_step_ingredients_unit_id_units"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_step_ingredients")),
    )
    op.create_index(
        op.f("ix_step_ingredients_ingredient_id"),
        "step_ingredients",
        ["ingredient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_step_ingredients_public_id"), "step_ingredients", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_step_ingredients_step_id"), "step_ingredients", ["step_id"], unique=False
    )
    op.create_index(
        op.f("ix_step_ingredients_sub_recipe_id"),
        "step_ingredients",
        ["sub_recipe_id"],
        unique=False,
    )
    op.create_table(
        "step_equipment_translations",
        sa.Column("step_equipment_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["step_equipment_id"],
            ["step_equipment.id"],
            name=op.f("fk_step_equipment_translations_step_equipment_id_step_equipment"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "step_equipment_id", "locale", name=op.f("pk_step_equipment_translations")
        ),
    )
    op.create_table(
        "step_ingredient_translations",
        sa.Column("step_ingredient_id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["step_ingredient_id"],
            ["step_ingredients.id"],
            name=op.f("fk_step_ingredient_translations_step_ingredient_id_step_ingredients"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "step_ingredient_id", "locale", name=op.f("pk_step_ingredient_translations")
        ),
    )
    # users and stored_files reference each other, so the avatar key is added
    # once both tables exist; create_table skips a use_alter constraint.
    with op.batch_alter_table("users") as batch:
        batch.create_foreign_key(
            "fk_users_avatar_file_id_stored_files",
            "stored_files",
            ["avatar_file_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("fk_users_avatar_file_id_stored_files", type_="foreignkey")
    op.drop_table("step_ingredient_translations")
    op.drop_table("step_equipment_translations")
    op.drop_index(op.f("ix_step_ingredients_sub_recipe_id"), table_name="step_ingredients")
    op.drop_index(op.f("ix_step_ingredients_step_id"), table_name="step_ingredients")
    op.drop_index(op.f("ix_step_ingredients_public_id"), table_name="step_ingredients")
    op.drop_index(op.f("ix_step_ingredients_ingredient_id"), table_name="step_ingredients")
    op.drop_table("step_ingredients")
    op.drop_index(op.f("ix_step_equipment_step_id"), table_name="step_equipment")
    op.drop_index(op.f("ix_step_equipment_public_id"), table_name="step_equipment")
    op.drop_index(op.f("ix_step_equipment_equipment_id"), table_name="step_equipment")
    op.drop_table("step_equipment")
    op.drop_table("recipe_step_translations")
    op.drop_index(
        "uq_recipe_ratings_user_id_recipe_id_original",
        table_name="recipe_ratings",
        postgresql_where=sa.text("variation_id IS NULL"),
        sqlite_where=sa.text("variation_id IS NULL"),
    )
    op.drop_index(op.f("ix_recipe_ratings_variation_id"), table_name="recipe_ratings")
    op.drop_index(op.f("ix_recipe_ratings_recipe_id"), table_name="recipe_ratings")
    op.drop_index(op.f("ix_recipe_ratings_public_id"), table_name="recipe_ratings")
    op.drop_table("recipe_ratings")
    op.drop_table("recipe_ingredient_translations")
    op.drop_index(op.f("ix_cook_events_variation_id"), table_name="cook_events")
    op.drop_index(op.f("ix_cook_events_user_id"), table_name="cook_events")
    op.drop_index(op.f("ix_cook_events_recipe_id"), table_name="cook_events")
    op.drop_index(op.f("ix_cook_events_public_id"), table_name="cook_events")
    op.drop_index(op.f("ix_cook_events_cooked_on"), table_name="cook_events")
    op.drop_table("cook_events")
    op.drop_index(op.f("ix_shopping_items_public_id"), table_name="shopping_items")
    op.drop_index(op.f("ix_shopping_items_list_id"), table_name="shopping_items")
    op.drop_table("shopping_items")
    op.drop_index(op.f("ix_recipe_variations_recipe_id"), table_name="recipe_variations")
    op.drop_index(op.f("ix_recipe_variations_public_id"), table_name="recipe_variations")
    op.drop_index(op.f("ix_recipe_variations_author_id"), table_name="recipe_variations")
    op.drop_table("recipe_variations")
    op.drop_index(op.f("ix_recipe_user_shares_user_id"), table_name="recipe_user_shares")
    op.drop_table("recipe_user_shares")
    op.drop_table("recipe_translations")
    op.drop_index(op.f("ix_recipe_tags_tag_id"), table_name="recipe_tags")
    op.drop_table("recipe_tags")
    op.drop_index(op.f("ix_recipe_steps_recipe_id"), table_name="recipe_steps")
    op.drop_index(op.f("ix_recipe_steps_public_id"), table_name="recipe_steps")
    op.drop_table("recipe_steps")
    op.drop_index(op.f("ix_recipe_revisions_recipe_id"), table_name="recipe_revisions")
    op.drop_index(op.f("ix_recipe_revisions_public_id"), table_name="recipe_revisions")
    op.drop_index(op.f("ix_recipe_revisions_created"), table_name="recipe_revisions")
    op.drop_index(op.f("ix_recipe_revisions_author_id"), table_name="recipe_revisions")
    op.drop_table("recipe_revisions")
    op.drop_index(op.f("ix_recipe_peer_shares_peer_id"), table_name="recipe_peer_shares")
    op.drop_table("recipe_peer_shares")
    op.drop_index("ix_recipe_notes_recipe_id", table_name="recipe_notes")
    op.drop_index(op.f("ix_recipe_notes_public_id"), table_name="recipe_notes")
    op.drop_table("recipe_notes")
    op.drop_index(op.f("ix_recipe_mirrors_peer_id"), table_name="recipe_mirrors")
    op.drop_table("recipe_mirrors")
    op.drop_index(op.f("ix_recipe_ingredients_sub_recipe_id"), table_name="recipe_ingredients")
    op.drop_index(op.f("ix_recipe_ingredients_recipe_id"), table_name="recipe_ingredients")
    op.drop_index(op.f("ix_recipe_ingredients_public_id"), table_name="recipe_ingredients")
    op.drop_index(op.f("ix_recipe_ingredients_ingredient_id"), table_name="recipe_ingredients")
    op.drop_table("recipe_ingredients")
    op.drop_index(op.f("ix_recipe_group_shares_group_id"), table_name="recipe_group_shares")
    op.drop_table("recipe_group_shares")
    op.drop_index(op.f("ix_recipe_favourites_recipe_id"), table_name="recipe_favourites")
    op.drop_table("recipe_favourites")
    op.drop_index(op.f("ix_recipe_co_editors_user_id"), table_name="recipe_co_editors")
    op.drop_table("recipe_co_editors")
    op.drop_index("ix_meal_plan_entries_user_date", table_name="meal_plan_entries")
    op.drop_index(op.f("ix_meal_plan_entries_public_id"), table_name="meal_plan_entries")
    op.drop_index(op.f("ix_meal_plan_entries_household_id"), table_name="meal_plan_entries")
    op.drop_table("meal_plan_entries")
    op.drop_table("stored_file_contents")
    op.drop_index(op.f("ix_shopping_list_members_user_id"), table_name="shopping_list_members")
    op.drop_table("shopping_list_members")
    op.drop_index(op.f("ix_recipes_status"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_public_id"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_owner_id"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_mirror_peer_id"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_based_on_recipe_id"), table_name="recipes")
    op.drop_table("recipes")
    op.drop_table("peer_suggestion_dismissals")
    op.drop_index(op.f("ix_peer_invitations_public_id"), table_name="peer_invitations")
    op.drop_index(op.f("ix_peer_invitations_expires_at"), table_name="peer_invitations")
    op.drop_table("peer_invitations")
    op.drop_index(op.f("ix_peer_incoming_recipes_public_id"), table_name="peer_incoming_recipes")
    op.drop_index(op.f("ix_peer_incoming_recipes_peer_id"), table_name="peer_incoming_recipes")
    op.drop_table("peer_incoming_recipes")
    op.drop_index(op.f("ix_peer_inbox_public_id"), table_name="peer_inbox")
    op.drop_index("ix_peer_inbox_peer_next", table_name="peer_inbox")
    op.drop_table("peer_inbox")
    op.drop_table("peer_channels")
    op.drop_index(op.f("ix_peer_channel_events_public_id"), table_name="peer_channel_events")
    op.drop_index("ix_peer_channel_events_peer_seq", table_name="peer_channel_events")
    op.drop_table("peer_channel_events")
    op.drop_index(op.f("ix_peer_catalogue_mappings_unit_id"), table_name="peer_catalogue_mappings")
    op.drop_index(op.f("ix_peer_catalogue_mappings_tag_id"), table_name="peer_catalogue_mappings")
    op.drop_index(
        op.f("ix_peer_catalogue_mappings_ingredient_id"), table_name="peer_catalogue_mappings"
    )
    op.drop_index(
        op.f("ix_peer_catalogue_mappings_equipment_id"), table_name="peer_catalogue_mappings"
    )
    op.drop_table("peer_catalogue_mappings")
    op.drop_index(op.f("ix_oauth_tokens_public_id"), table_name="oauth_tokens")
    op.drop_index(op.f("ix_oauth_tokens_grant_id"), table_name="oauth_tokens")
    op.drop_table("oauth_tokens")
    op.drop_index(op.f("ix_notice_acknowledgements_user_id"), table_name="notice_acknowledgements")
    op.drop_table("notice_acknowledgements")
    op.drop_index(op.f("ix_kitchen_equipment_equipment_id"), table_name="kitchen_equipment")
    op.drop_table("kitchen_equipment")
    op.drop_table("ingredient_translations")
    op.drop_table("ingredient_conversions")
    op.drop_table("ingredient_aliases")
    op.drop_index(op.f("ix_food_restrictions_user_id"), table_name="food_restrictions")
    op.drop_index(op.f("ix_food_restrictions_public_id"), table_name="food_restrictions")
    op.drop_table("food_restrictions")
    op.drop_index("ix_webhook_deliveries_subscription_created", table_name="webhook_deliveries")
    op.drop_index(op.f("ix_webhook_deliveries_subject_user_id"), table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_status_next", table_name="webhook_deliveries")
    op.drop_index(op.f("ix_webhook_deliveries_public_id"), table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_public_id"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index(op.f("ix_user_group_members_group_id"), table_name="user_group_members")
    op.drop_table("user_group_members")
    op.drop_table("unit_translations")
    op.drop_index(op.f("ix_trusted_devices_user_id"), table_name="trusted_devices")
    op.drop_index(op.f("ix_trusted_devices_public_id"), table_name="trusted_devices")
    op.drop_table("trusted_devices")
    op.drop_table("tag_translations")
    op.drop_index(op.f("ix_stored_files_public_id"), table_name="stored_files")
    op.drop_index(op.f("ix_stored_files_creator_id"), table_name="stored_files")
    op.drop_table("stored_files")
    op.drop_index(op.f("ix_shopping_lists_public_id"), table_name="shopping_lists")
    op.drop_index(op.f("ix_shopping_lists_owner_id"), table_name="shopping_lists")
    op.drop_index(op.f("ix_shopping_lists_household_id"), table_name="shopping_lists")
    op.drop_table("shopping_lists")
    op.drop_index(op.f("ix_shopping_list_notes_user_id"), table_name="shopping_list_notes")
    op.drop_index(op.f("ix_shopping_list_notes_public_id"), table_name="shopping_list_notes")
    op.drop_table("shopping_list_notes")
    op.drop_index(op.f("ix_security_events_target_user_id"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_public_id"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_event_type"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_created"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_actor_id"), table_name="security_events")
    op.drop_table("security_events")
    op.drop_index(op.f("ix_personal_access_tokens_user_id"), table_name="personal_access_tokens")
    op.drop_index(op.f("ix_personal_access_tokens_public_id"), table_name="personal_access_tokens")
    op.drop_table("personal_access_tokens")
    op.drop_index(op.f("ix_peers_public_id"), table_name="peers")
    op.drop_table("peers")
    op.drop_index(op.f("ix_passkeys_user_id"), table_name="passkeys")
    op.drop_index(op.f("ix_passkeys_public_id"), table_name="passkeys")
    op.drop_table("passkeys")
    op.drop_index(op.f("ix_oauth_grants_user_id"), table_name="oauth_grants")
    op.drop_index(op.f("ix_oauth_grants_public_id"), table_name="oauth_grants")
    op.drop_index(op.f("ix_oauth_grants_client_id"), table_name="oauth_grants")
    op.drop_table("oauth_grants")
    op.drop_index(op.f("ix_notices_public_id"), table_name="notices")
    op.drop_table("notices")
    op.drop_index(op.f("ix_legal_versions_public_id"), table_name="legal_versions")
    op.drop_table("legal_versions")
    op.drop_index(op.f("ix_kitchens_public_id"), table_name="kitchens")
    op.drop_table("kitchens")
    op.drop_index(op.f("ix_ingredients_public_id"), table_name="ingredients")
    op.drop_index(op.f("ix_ingredients_owner_id"), table_name="ingredients")
    op.drop_index(op.f("ix_ingredients_family_id"), table_name="ingredients")
    op.drop_table("ingredients")
    op.drop_table("ingredient_family_translations")
    op.drop_table("ingredient_category_translations")
    op.drop_index(op.f("ix_household_members_household_id"), table_name="household_members")
    op.drop_table("household_members")
    op.drop_index(op.f("ix_household_invitations_public_id"), table_name="household_invitations")
    op.drop_index(op.f("ix_household_invitations_invitee_id"), table_name="household_invitations")
    op.drop_table("household_invitations")
    op.drop_table("equipment_translations")
    op.drop_table("equipment_aliases")
    op.drop_index(op.f("ix_api_keys_public_id"), table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index(op.f("ix_agent_calls_user_id"), table_name="agent_calls")
    op.drop_index("ix_agent_calls_token_called_at", table_name="agent_calls")
    op.drop_index(op.f("ix_agent_calls_public_id"), table_name="agent_calls")
    op.drop_table("agent_calls")
    op.drop_index(op.f("ix_webhook_subscriptions_public_id"), table_name="webhook_subscriptions")
    op.drop_table("webhook_subscriptions")
    op.drop_index(op.f("ix_users_public_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_user_groups_public_id"), table_name="user_groups")
    op.drop_table("user_groups")
    op.drop_index(op.f("ix_units_public_id"), table_name="units")
    op.drop_table("units")
    op.drop_index(op.f("ix_tags_public_id"), table_name="tags")
    op.drop_table("tags")
    op.drop_table("settings")
    op.drop_table("seeded_keys")
    op.drop_index(op.f("ix_oauth_clients_public_id"), table_name="oauth_clients")
    op.drop_table("oauth_clients")
    op.drop_index(op.f("ix_ingredient_families_public_id"), table_name="ingredient_families")
    op.drop_table("ingredient_families")
    op.drop_index(op.f("ix_ingredient_categories_public_id"), table_name="ingredient_categories")
    op.drop_table("ingredient_categories")
    op.drop_index(op.f("ix_households_public_id"), table_name="households")
    op.drop_table("households")
    op.drop_index(op.f("ix_equipment_public_id"), table_name="equipment")
    op.drop_table("equipment")
