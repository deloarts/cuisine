"""The OAuth protocol rules: PKCE, redirect URIs, scopes, the redirect host
allowlist and lifetimes."""

import base64
import hashlib
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

from src.platform.domain.exceptions import OAuthRequestError
from src.platform.domain.services.oauth_rules import access_token_expiry
from src.platform.domain.services.oauth_rules import assert_code_challenge
from src.platform.domain.services.oauth_rules import grant_expiry
from src.platform.domain.services.oauth_rules import host_allowed
from src.platform.domain.services.oauth_rules import normalise_hosts
from src.platform.domain.services.oauth_rules import pkce_matches
from src.platform.domain.services.oauth_rules import redirect_matches
from src.platform.domain.services.oauth_rules import requested_permissions
from src.platform.domain.services.oauth_rules import resolve_redirect
from src.platform.domain.services.oauth_rules import validate_redirect_uri
from src.platform.domain.services.oauth_rules import with_query

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def test_pkce_s256() -> None:
    # The example of RFC 7636 appendix B.
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert _challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert pkce_matches(verifier, "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
    assert not pkce_matches(verifier[:-1] + "Y", "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
    # Too short to be a verifier at all.
    assert not pkce_matches("short", _challenge("short"))


def test_only_s256_challenges_are_accepted() -> None:
    challenge = _challenge("a" * 43)
    assert assert_code_challenge(challenge, "S256") == challenge
    for method in (None, "plain"):
        with pytest.raises(OAuthRequestError):
            assert_code_challenge(challenge, method)
    with pytest.raises(OAuthRequestError):
        assert_code_challenge(None, "S256")
    with pytest.raises(OAuthRequestError):
        assert_code_challenge("not-a-challenge", "S256")


@pytest.mark.parametrize(
    "uri",
    [
        "https://chatgpt.com/connector_platform_oauth_redirect",
        "https://claude.ai/api/mcp/auth_callback",
        "http://localhost:33418/callback",
        "http://127.0.0.1/cb",
    ],
)
def test_valid_redirect_uris(uri: str) -> None:
    assert validate_redirect_uri(uri) == uri


@pytest.mark.parametrize(
    "uri",
    [
        "",
        "http://example.com/cb",
        "https://example.com/cb#fragment",
        "https://user:pass@example.com/cb",
        "https://*.example.com/cb",
        "/relative",
        "custom-scheme://cb",
    ],
)
def test_invalid_redirect_uris(uri: str) -> None:
    with pytest.raises(OAuthRequestError) as raised:
        validate_redirect_uri(uri)
    assert raised.value.error == "invalid_redirect_uri"


def test_redirects_match_exactly_except_loopback_ports() -> None:
    assert redirect_matches("https://a.com/cb", "https://a.com/cb")
    assert not redirect_matches("https://a.com/cb", "https://a.com/cb/")
    assert not redirect_matches("https://a.com/cb", "https://a.com:8443/cb")
    assert redirect_matches("http://127.0.0.1:1000/cb", "http://127.0.0.1:2000/cb")
    assert not redirect_matches("http://127.0.0.1:1000/cb", "http://127.0.0.1:2000/other")


def test_resolving_the_redirect_of_a_request() -> None:
    assert resolve_redirect(["https://a.com/cb"], None) == "https://a.com/cb"
    assert resolve_redirect(["https://a.com/1", "https://a.com/2"], None) is None
    assert resolve_redirect(["https://a.com/1", "https://a.com/2"], "https://a.com/2")
    assert resolve_redirect(["https://a.com/1"], "https://b.com/1") is None


def test_with_query_keeps_the_existing_query() -> None:
    assert with_query("https://a.com/cb", {"code": "c", "state": None}) == "https://a.com/cb?code=c"
    assert with_query("https://a.com/cb?x=1", {"code": "c d"}) == "https://a.com/cb?x=1&code=c+d"


def test_scopes() -> None:
    every = ["use:mcp", "write:recipes", "write:ingredients"]
    assert requested_permissions(None) == every
    assert requested_permissions("openid offline_access") == every
    assert requested_permissions("use:mcp") == ["use:mcp"]
    assert requested_permissions("write:recipes") == ["use:mcp", "write:recipes"]
    assert requested_permissions("write:users write:recipes") == ["use:mcp", "write:recipes"]


def test_the_host_allowlist() -> None:
    assert normalise_hosts([" ChatGPT.com ", "chatgpt.com", "", "claude.ai."]) == [
        "chatgpt.com",
        "claude.ai",
    ]
    for bad in ("*.ai", "https://claude.ai", "claude.ai/path", "claude.ai:443"):
        with pytest.raises(ValueError):
            normalise_hosts([bad])
    assert host_allowed("https://chatgpt.com/cb", [])
    assert host_allowed("https://chatgpt.com/cb", ["chatgpt.com"])
    assert not host_allowed("https://evil.chatgpt.com/cb", ["chatgpt.com"])


def test_lifetimes() -> None:
    assert grant_expiry(NOW, 30, 90) == NOW + timedelta(days=30)
    assert grant_expiry(NOW, 0, 90) == NOW + timedelta(days=90)
    assert grant_expiry(NOW, 0, 0) is None
    assert access_token_expiry(NOW, None) == NOW + timedelta(hours=1)
    soon = NOW + timedelta(minutes=10)
    assert access_token_expiry(NOW, soon) == soon
