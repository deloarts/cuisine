"""The passkey routes, with a fake verifier standing in for the browser and
the authenticator, since real WebAuthn needs both. They run on an ordinary
account, since the system user cannot use passkeys."""

from typing import Any

import httpx
import pytest

from src.platform.adapters.inbound.api import deps
from src.platform.domain.exceptions import PasskeyRejectedError
from src.platform.ports.outbound.passkey_verifier import PasskeyOptions
from src.platform.ports.outbound.passkey_verifier import VerifiedPasskeyRegistration
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login


class FakeVerifier:
    """Accepts a credential whose `rawId` and `challenge` match what it
    handed out; refuses everything else."""

    def __init__(self) -> None:
        self.counter = 0

    def _options(self) -> PasskeyOptions:
        self.counter += 1
        challenge = f"challenge-{self.counter}"
        return PasskeyOptions(options={"challenge": challenge}, challenge=challenge)

    def registration_options(self, **_: Any) -> PasskeyOptions:
        return self._options()

    def authentication_options(self) -> PasskeyOptions:
        return self._options()

    def verify_registration(
        self, *, credential: dict[str, Any], challenge: str
    ) -> VerifiedPasskeyRegistration:
        assert credential["challenge"] == challenge
        return VerifiedPasskeyRegistration(
            credential_id=credential["rawId"].encode(),
            public_key=b"public-key",
            sign_count=0,
            backed_up=True,
            transports=["internal"],
        )

    def credential_id_of(self, credential: dict[str, Any]) -> bytes | None:
        raw = credential.get("rawId")
        return raw.encode() if isinstance(raw, str) else None

    def verify_authentication(
        self, *, credential: dict[str, Any], challenge: str, public_key: bytes, sign_count: int
    ) -> int:
        if credential.get("challenge") != challenge or credential.get("bad"):
            raise PasskeyRejectedError("did not verify")
        return sign_count + 1


@pytest.fixture(autouse=True)
def fake_verifier(monkeypatch: pytest.MonkeyPatch) -> FakeVerifier:
    verifier = FakeVerifier()
    monkeypatch.setattr(deps, "passkey_verifier", lambda: verifier)
    return verifier


@pytest.fixture
async def cook(admin: httpx.AsyncClient, make_user: MakeUser) -> httpx.AsyncClient:
    """The admin's client, signed in again as an ordinary account."""
    await make_user("cook", "cook-password-1")
    await login(admin, "cook@example.com", "cook-password-1")
    return admin


async def _register(client: httpx.AsyncClient) -> dict[str, Any]:
    options = (await client.post("/api/v1/web/users/me/passkeys/options", headers=CSRF)).json()
    challenge = options["options"]["challenge"]
    registered = await client.post(
        "/api/v1/web/users/me/passkeys",
        headers=CSRF,
        json={
            "challenge_token": options["challenge_token"],
            "credential": {"rawId": "cred-1", "challenge": challenge},
            "name": "Laptop",
        },
    )
    assert registered.status_code == 201, registered.text
    body: dict[str, Any] = registered.json()
    return body


async def test_register_and_log_in_with_a_passkey(
    cook: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    passkey = await _register(cook)
    assert passkey["name"] == "Laptop"

    options = (await other_client.post("/api/v1/auth/login/passkey/options")).json()
    login = await other_client.post(
        "/api/v1/auth/login/passkey",
        json={
            "challenge_token": options["challenge_token"],
            "credential": {"rawId": "cred-1", "challenge": options["options"]["challenge"]},
        },
    )
    assert login.status_code == 200, login.text
    assert (await other_client.get("/api/v1/web/users/me")).json()["email"] == "cook@example.com"


async def test_passkey_challenge_cannot_be_reused(
    cook: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    await _register(cook)
    options = (await other_client.post("/api/v1/auth/login/passkey/options")).json()
    body = {
        "challenge_token": options["challenge_token"],
        "credential": {"rawId": "cred-1", "challenge": options["options"]["challenge"]},
    }
    assert (await other_client.post("/api/v1/auth/login/passkey", json=body)).status_code == 200
    assert (await other_client.post("/api/v1/auth/login/passkey", json=body)).status_code == 401


async def test_unknown_or_rejected_passkey_is_refused(
    cook: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    await _register(cook)
    for credential in ({"rawId": "nope"}, {"rawId": "cred-1", "bad": True}):
        options = (await other_client.post("/api/v1/auth/login/passkey/options")).json()
        credential["challenge"] = options["options"]["challenge"]
        refused = await other_client.post(
            "/api/v1/auth/login/passkey",
            json={"challenge_token": options["challenge_token"], "credential": credential},
        )
        assert refused.status_code == 401


async def test_rename_and_remove_a_passkey(cook: httpx.AsyncClient) -> None:
    passkey = await _register(cook)
    renamed = await cook.patch(
        f"/api/v1/web/users/me/passkeys/{passkey['id']}", headers=CSRF, json={"name": "Phone"}
    )
    assert renamed.json()["name"] == "Phone"
    removed = await cook.delete(f"/api/v1/web/users/me/passkeys/{passkey['id']}", headers=CSRF)
    assert removed.status_code == 204
    assert (await cook.get("/api/v1/web/users/me/passkeys")).json() == []


async def test_the_system_user_cannot_register_a_passkey(admin: httpx.AsyncClient) -> None:
    options = await admin.post("/api/v1/web/users/me/passkeys/options", headers=CSRF)
    assert options.status_code == 403
