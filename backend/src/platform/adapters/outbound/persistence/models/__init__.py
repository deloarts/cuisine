"""Every ORM model, imported here so Alembic's metadata sees them all."""

from src.platform.adapters.outbound.persistence.models.agent_call_models import AgentCallModel
from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.legal_models import LegalVersionModel
from src.platform.adapters.outbound.persistence.models.notice_models import (
    NoticeAcknowledgementModel,
)
from src.platform.adapters.outbound.persistence.models.notice_models import NoticeModel
from src.platform.adapters.outbound.persistence.models.oauth_models import OAuthClientModel
from src.platform.adapters.outbound.persistence.models.oauth_models import OAuthGrantModel
from src.platform.adapters.outbound.persistence.models.oauth_models import OAuthTokenModel
from src.platform.adapters.outbound.persistence.models.peer_channel_models import (
    PeerChannelEventModel,
)
from src.platform.adapters.outbound.persistence.models.peer_channel_models import PeerChannelModel
from src.platform.adapters.outbound.persistence.models.peer_channel_models import PeerInboxModel
from src.platform.adapters.outbound.persistence.models.peer_models import PeerInvitationModel
from src.platform.adapters.outbound.persistence.models.peer_models import PeerModel
from src.platform.adapters.outbound.persistence.models.security_models import ApiKeyModel
from src.platform.adapters.outbound.persistence.models.security_models import PasskeyModel
from src.platform.adapters.outbound.persistence.models.security_models import (
    PersonalAccessTokenModel,
)
from src.platform.adapters.outbound.persistence.models.security_models import SecurityEventModel
from src.platform.adapters.outbound.persistence.models.security_models import TrustedDeviceModel
from src.platform.adapters.outbound.persistence.models.security_models import UserSessionModel
from src.platform.adapters.outbound.persistence.models.settings_model import SettingsModel
from src.platform.adapters.outbound.persistence.models.stored_file_models import (
    StoredFileContentModel,
)
from src.platform.adapters.outbound.persistence.models.stored_file_models import StoredFileModel
from src.platform.adapters.outbound.persistence.models.user_models import UserGroupMemberModel
from src.platform.adapters.outbound.persistence.models.user_models import UserGroupModel
from src.platform.adapters.outbound.persistence.models.user_models import UserModel
from src.platform.adapters.outbound.persistence.models.webhook_models import WebhookDeliveryModel
from src.platform.adapters.outbound.persistence.models.webhook_models import (
    WebhookSubscriptionModel,
)

__all__ = [
    "AgentCallModel",
    "ApiKeyModel",
    "Base",
    "LegalVersionModel",
    "NoticeAcknowledgementModel",
    "NoticeModel",
    "OAuthClientModel",
    "OAuthGrantModel",
    "OAuthTokenModel",
    "PasskeyModel",
    "PeerChannelEventModel",
    "PeerChannelModel",
    "PeerInboxModel",
    "PeerInvitationModel",
    "PeerModel",
    "PersonalAccessTokenModel",
    "SecurityEventModel",
    "SettingsModel",
    "StoredFileContentModel",
    "StoredFileModel",
    "TrustedDeviceModel",
    "UserGroupMemberModel",
    "UserGroupModel",
    "UserModel",
    "UserSessionModel",
    "WebhookDeliveryModel",
    "WebhookSubscriptionModel",
]
