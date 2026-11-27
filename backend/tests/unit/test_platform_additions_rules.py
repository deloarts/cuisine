"""The rules behind maintenance mode, the privacy statement, backups, mail
templates and the log redactor."""

from datetime import UTC
from datetime import date
from datetime import datetime

from src.platform.application.services.mailer import plain_text
from src.platform.domain.entities.legal import LegalKind
from src.platform.domain.entities.legal import LegalVersion
from src.platform.domain.entities.legal import PrivacyMode
from src.platform.domain.entities.settings import MailTemplateText
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.domain.entities.user import User
from src.platform.domain.services.backup_rules import backup_retention
from src.platform.domain.services.legal_rules import acknowledgement_pending
from src.platform.domain.services.legal_rules import privacy_mode_of
from src.platform.domain.services.mail_templates import locale_chain
from src.platform.domain.services.mail_templates import pick_override
from src.platform.domain.services.maintenance_rules import refused_in_maintenance
from src.platform.domain.services.privacy_draft import PRIVACY_MODE_MARKER
from src.platform.domain.services.privacy_draft import render_privacy_statement
from src.platform.domain.value_objects.mail import MailTemplateKind
from src.platform.infrastructure.logging.ring_buffer import Redactor

NOW = datetime(2026, 11, 21, tzinfo=UTC)


def test_maintenance_refuses_writes_but_not_the_way_out() -> None:
    assert refused_in_maintenance("POST", "/api/v1/web/recipes")
    assert refused_in_maintenance("DELETE", "/api/v1/web/users/x")
    assert refused_in_maintenance("GET", "/api/v1/mcp")
    assert not refused_in_maintenance("GET", "/api/v1/web/recipes")
    assert not refused_in_maintenance("POST", "/api/v1/auth/login")
    assert not refused_in_maintenance("PUT", "/api/v1/web/settings/maintenance")


def test_privacy_mode_in_plain_words() -> None:
    instance = privacy_mode_of(PrivacySettings("instance", False))
    private = privacy_mode_of(PrivacySettings("household", False))
    choice = privacy_mode_of(PrivacySettings("private", True))
    assert (instance.mode, private.mode, choice.mode) == (
        PrivacyMode.INSTANCE,
        PrivacyMode.PRIVATE,
        PrivacyMode.USER_CHOICE,
    )
    text = render_privacy_statement(f"# Intro\n\n{PRIVACY_MODE_MARKER}\n\nEnd", private, "de-AT")
    assert "**Privat**" in text and "für den eigenen Haushalt sichtbar" in text
    assert "Wer ihn nicht akzeptiert, kann Cuisine nicht nutzen" in text
    appended = render_privacy_statement("No marker here.", instance, "en-GB")
    assert appended.startswith("No marker here.") and "**instance**" in appended


def test_acknowledgement_is_pending_for_people_until_the_current_version() -> None:
    user = User(full_name="U", email="u@example.com", created=NOW, hashed_password="")
    version = LegalVersion(kind=LegalKind.PRIVACY, version=2, published_at=NOW)
    assert not acknowledgement_pending(user, None)
    assert acknowledgement_pending(user, version)
    user.privacy_acknowledged_version = 1
    assert acknowledgement_pending(user, version)
    user.privacy_acknowledged_version = 2
    assert not acknowledgement_pending(user, version)
    service = User(
        full_name="S",
        email="s@example.com",
        created=NOW,
        hashed_password="",
        is_service_account=True,
    )
    assert not acknowledgement_pending(service, version)


def test_backups_keep_deleted_data_for_keep_days_and_one() -> None:
    retention = backup_retention(14, date(2026, 11, 21))
    assert retention.gone_by == date(2026, 12, 6)


def test_template_resolution_skips_blank_bodies() -> None:
    chain = locale_chain("de-AT", "en-GB")
    assert chain == ["de-AT", "en-GB"]
    overrides = {
        "test_mail": {
            "de-AT": MailTemplateText(subject="x", body="  "),
            "en-GB": MailTemplateText(subject="Hi", body="<p>Hi</p>"),
        }
    }
    picked = pick_override(overrides, MailTemplateKind.TEST_MAIL, chain)
    assert picked is not None and picked[0] == "en-GB"
    assert pick_override({}, MailTemplateKind.TEST_MAIL, chain) is None


def test_plain_text_alternative_drops_markup_and_styles() -> None:
    html = "<html><head><style>p{}</style></head><body><p>Hello &amp; welcome</p></body></html>"
    assert plain_text(html) == "Hello & welcome"


def test_redactor_hides_configured_and_shaped_secrets() -> None:
    redact = Redactor(["the-real-secret-key", "short"])
    text = redact(
        "key the-real-secret-key; password=abc123; postgresql://cuisine:pw123@db/x; "
        "cuisine_pat_abcdef; whsec_AAAABBBB; short stays"
    )
    for secret in ("the-real-secret-key", "abc123", "pw123", "abcdef", "AAAABBBB"):
        assert secret not in text
    assert "short stays" in text
