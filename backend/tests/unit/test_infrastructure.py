"""The security adapters: tokens, the secret box, opaque secrets, TOTP, the
in-process throttle and the image processor."""

import struct
import zlib
from io import BytesIO

import pytest
from PIL import Image

from src.platform.adapters.outbound.external.login_attempts import InMemoryLoginAttemptTracker
from src.platform.adapters.outbound.external.pillow_image_processor import PillowImageProcessor
from src.platform.adapters.outbound.external.replay_guard import InMemoryReplayGuard
from src.platform.domain.exceptions import FileTypeNotAcceptedError
from src.platform.domain.value_objects import token_scope
from src.platform.infrastructure.config.settings import cfg
from src.platform.infrastructure.security import secret_box
from src.platform.infrastructure.security.hashing import BcryptPasswordHasher
from src.platform.infrastructure.security.opaque_secret import Sha256SecretHasher
from src.platform.infrastructure.security.token import JwtTokenService


def test_session_token_round_trip_and_tamper() -> None:
    service = JwtTokenService(secret_key="k" * 32)
    token = service.session_token(7, 3, "sid-1")
    claims = service.read(token)
    assert claims is not None
    assert (claims.sub, claims.ver, claims.sid, claims.scope) == ("7", 3, "sid-1", "")
    assert service.read(token + "x") is None
    assert JwtTokenService(secret_key="o" * 32).read(token) is None


def test_bridge_tokens_carry_their_scope() -> None:
    service = JwtTokenService(secret_key="k" * 32)
    partial = service.read(service.partial_token(1))
    setup = service.read(service.setup_token(1, 0))
    challenge = service.read(service.passkey_challenge_token("abc", token_scope.PASSKEY_LOGIN))
    assert partial is not None and partial.scope == token_scope.TOTP_PENDING
    assert setup is not None and setup.scope == token_scope.TOTP_SETUP
    assert challenge is not None and challenge.chl == "abc" and challenge.sub is None


def test_secret_box_round_trip_and_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    stored = secret_box.encrypt_secret("smtp-password")
    assert stored.startswith(secret_box.ENCRYPTED_PREFIX)
    assert "smtp-password" not in stored
    assert secret_box.decrypt_secret(stored) == "smtp-password"

    old_key = cfg.security.encryption_key
    monkeypatch.setattr(cfg.security, "encryption_key", "new-key")
    with pytest.raises(secret_box.SecretDecryptionError):
        secret_box.decrypt_secret(stored)
    monkeypatch.setattr(cfg.security, "encryption_key_previous", old_key)
    assert secret_box.decrypt_secret(stored) == "smtp-password"


def test_opaque_secrets_hash_deterministically() -> None:
    hasher = Sha256SecretHasher()
    secret = hasher.generate("cuisine_pat_")
    assert secret.startswith("cuisine_pat_")
    assert hasher.hash(secret) == hasher.hash(secret)
    assert hasher.display_prefix(secret, "cuisine_pat_") == secret[: len("cuisine_pat_") + 8]


async def test_password_hasher_round_trip() -> None:
    hasher = BcryptPasswordHasher()
    hashed = await hasher.hash("é" * 40)  # 80 bytes, cut at bcrypt's 72
    assert await hasher.verify("é" * 40, hashed)
    assert not await hasher.verify("wrong", hashed)
    assert not await hasher.verify("x", "!")


async def test_in_memory_throttle_locks_at_the_limit() -> None:
    tracker = InMemoryLoginAttemptTracker()
    assert not await tracker.record_failure("k", limit=2, lockout_seconds=60)
    assert await tracker.record_failure("k", limit=2, lockout_seconds=60)
    assert await tracker.lock_ttl("k") > 0
    assert not await tracker.record_failure("free", limit=0, lockout_seconds=60)


async def test_replay_guard_claims_once() -> None:
    guard = InMemoryReplayGuard()
    assert await guard.consume_once("code", 60)
    assert not await guard.consume_once("code", 60)


def _encode(image: Image.Image, fmt: str, **kwargs: object) -> bytes:
    out = BytesIO()
    image.save(out, format=fmt, **kwargs)
    return out.getvalue()


def test_image_processor_applies_orientation_and_drops_exif() -> None:
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° clockwise on display
    exif[0x8825] = {2: (48.0, 12.0, 0.0)}  # GPS
    data = _encode(Image.new("RGB", (80, 40), "white"), "JPEG", exif=exif.tobytes())

    result = PillowImageProcessor(max_edge=2560, thumbnail_edge=20).process_sync(data)

    assert (result.width, result.height) == (40, 80)
    with Image.open(BytesIO(result.data)) as stored:
        assert stored.format == "WEBP"
        assert not stored.getexif()
    with Image.open(BytesIO(result.thumbnail)) as thumb:
        assert max(thumb.size) == 20


def test_image_processor_shrinks_large_images_and_keeps_alpha() -> None:
    data = _encode(Image.new("RGBA", (1000, 500), (0, 0, 0, 0)), "PNG")
    result = PillowImageProcessor(max_edge=200, thumbnail_edge=50).process_sync(data)
    assert (result.width, result.height) == (200, 100)
    with Image.open(BytesIO(result.data)) as stored:
        assert stored.mode == "RGBA"


async def test_image_processor_refuses_garbage() -> None:
    with pytest.raises(FileTypeNotAcceptedError):
        await PillowImageProcessor(100, 10).process(b"<svg onload=alert(1)>")


def _png_header_only(width: int, height: int) -> bytes:
    """A PNG whose header claims `width` by `height` pixels, with a tiny
    IDAT chunk, so only the header is valid and nothing is ever decoded."""

    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = zlib.crc32(kind + body) & 0xFFFFFFFF
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00"))
        + chunk(b"IEND", b"")
    )


def test_image_processor_refuses_more_than_64_megapixels_before_decoding() -> None:
    # 70 MP lies between Pillow's own warning and error thresholds.
    data = _png_header_only(10_000, 7_000)
    with pytest.raises(FileTypeNotAcceptedError, match="too many pixels"):
        PillowImageProcessor(max_edge=2560, thumbnail_edge=480).process_sync(data)


def test_undecryptable_column_value_loads_as_unset() -> None:
    from src.platform.adapters.outbound.persistence.types import EncryptedString

    column = EncryptedString()
    stored = column.process_bind_param("secret", None)  # type: ignore[arg-type]
    assert stored is not None and stored.startswith(secret_box.ENCRYPTED_PREFIX)
    assert column.process_result_value(stored, None) == "secret"  # type: ignore[arg-type]
    assert column.process_result_value("enc:v1:garbage", None) is None  # type: ignore[arg-type]
