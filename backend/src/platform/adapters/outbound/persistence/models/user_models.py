from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import false
from sqlalchemy import true
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import EncryptedString
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class UserModel(PublicIdMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    show_nickname: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_systemuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_service_account: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    permissions: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    theme_preset: Mapped[str] = mapped_column(String(32), nullable=False)
    theme_surface: Mapped[str] = mapped_column(String(32), nullable=False)
    theme_primary: Mapped[str] = mapped_column(String(32), nullable=False)
    theme_dark_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    amount_style: Mapped[str] = mapped_column(
        String(16), nullable=False, default="decimals", server_default="decimals"
    )
    share_restrictions_with_hosts: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    default_recipe_visibility: Mapped[str | None] = mapped_column(String(16), nullable=True)
    show_name_on_public_recipes: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    show_name_on_paired_instances: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    recipe_show_tips: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    recipe_show_notes: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    recipe_show_cooked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    recipe_show_rating: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    recipe_highlight_mentions: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    keep_screen_on: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    # use_alter breaks the cycle with stored_files.creator_id, so the tables
    # can be created and dropped in either order.
    avatar_file_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "stored_files.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_users_avatar_file_id_stored_files",
        ),
        nullable=True,
    )
    privacy_acknowledged_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    privacy_acknowledged_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    consent_health_data_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    consent_ai_agents_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_logged_in: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    totp_secret: Mapped[str | None] = mapped_column(EncryptedString(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class UserGroupModel(PublicIdMixin, Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    permissions: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class UserGroupMemberModel(Base):
    __tablename__ = "user_group_members"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_groups.id", ondelete="CASCADE"), primary_key=True, index=True
    )
