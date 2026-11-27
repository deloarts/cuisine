"""
Settings environment and suite-wide fixtures.

`settings.py` builds its `cfg` singleton at import time, so this file sets
the environment before anything imports the app. The database is a
throwaway SQLite file, created per pytest session and deleted on exit; a
file rather than `sqlite://`, because an in-memory database is scoped to a
single connection and the app opens several. Nothing touches Redis: the
throttle and replay guard are swapped for their in-process versions.

If ENV_FILE is set this backs off entirely, since environment variables win
over an env file and would silently point the suite at a developer's real
database; the integration fixtures refuse anything but SQLite.
"""

import atexit
import os
import shutil
import tempfile

if not os.getenv("ENV_FILE"):
    _tmp_dir = tempfile.mkdtemp(prefix="cuisine-test-db-")
    atexit.register(shutil.rmtree, _tmp_dir, True)
    os.environ["DATABASE__URL"] = f"sqlite:///{_tmp_dir}/test.db"
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("DOMAIN", "http://localhost:5173")
    os.environ.setdefault("SECURITY__SECRET_KEY", "test-secret-key-test-secret-key-0")
    os.environ.setdefault("SECURITY__ENCRYPTION_KEY", "test-encryption-key")
    # Never contacted; the suite swaps every Redis user for a fake.
    os.environ.setdefault("REDIS__URL", "redis://localhost:6379/15")
    os.environ.setdefault("INIT__FULL_NAME", "Test Admin")
    os.environ.setdefault("INIT__MAIL", "admin@example.com")
    os.environ.setdefault("INIT__PASSWORD", "admin-password-1")

import bcrypt
import pytest

from src.platform.infrastructure.security import hashing


@pytest.fixture(autouse=True)
def _fast_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    """The minimum bcrypt cost, so every test that hashes a password does
    not pay 12 rounds. Verification reads the cost from the hash itself."""
    monkeypatch.setattr(hashing, "gensalt", lambda: bcrypt.gensalt(4))
