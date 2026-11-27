"""Application-wide constants: the API surfaces, the version and limits."""

import tomllib
from pathlib import Path


def _load_version() -> str:
    """Single source of truth for the app version: [project].version in
    pyproject.toml, which the image copies next to src/."""
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    return str(data["project"]["version"])


VERSION: str = _load_version()
NAME = "cuisine"
VERSION_HEADER = "X-Cuisine-Version"

# The login name of the system user. Every other account signs in with its
# e-mail address, which always holds an "@", so the name can never clash.
SYSTEM_LOGIN = "system"

API_AUTH = "/api/v1/auth"
API_WEB = "/api/v1/web"
API_PAT = "/api/v1/pat"
API_KEY = "/api/v1/key"
API_PUBLIC = "/api/v1/public"
API_MCP = "/api/v1/mcp"
# The OAuth endpoints hosted AI clients call server to server (register,
# token, revoke). The consent page lives in the web app instead.
API_OAUTH = "/api/v1/oauth"
# The peering surface for other Cuisine instances. The path carries the
# peering protocol version, not the API version.
API_PEERING = "/api/peering/v1"

# The custom header every cookie-authenticated unsafe request must carry.
CSRF_HEADER_NAME = "X-Requested-With"
CSRF_HEADER_VALUE = "cuisine"

# Upload limits. Images are re-encoded and shrunk, so their limit only
# guards the decoder; documents are stored as uploaded.
MAX_IMAGE_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_DOCUMENT_UPLOAD_BYTES = 20 * 1024 * 1024
# The longest edge of a stored image and of its thumbnail, in pixels.
IMAGE_MAX_EDGE = 2560
THUMBNAIL_MAX_EDGE = 480

# The rate limit of the anonymous public recipe pages, per client address:
# at most this many requests (JSON and images together) per window. A page
# of the public list loads its JSON and up to 24 thumbnails.
ANONYMOUS_REQUEST_LIMIT = 300
ANONYMOUS_REQUEST_WINDOW_SECONDS = 60
# The rate limit of the peering surface, per client address. A peer sends a
# few requests per change, and a catch-up fetches one recipe per request.
PEERING_REQUEST_LIMIT = 600
PEERING_REQUEST_WINDOW_SECONDS = 60
# The rate limits of the OAuth endpoints, per client address: the token and
# revoke calls of connected apps, and the open client registration, which
# a client calls once per connection.
OAUTH_REQUEST_LIMIT = 120
OAUTH_REQUEST_WINDOW_SECONDS = 60
OAUTH_REGISTRATION_LIMIT = 20
OAUTH_REGISTRATION_WINDOW_SECONDS = 3600

PAT_PREFIX = "cuisine_pat_"
API_KEY_PREFIX = "cuisine_ak_"
# OAuth: the access and refresh tokens a connected app holds, the one-time
# authorization code, and the id and secret of a registered client.
OAUTH_ACCESS_PREFIX = "cuisine_oat_"
OAUTH_REFRESH_PREFIX = "cuisine_ort_"
OAUTH_CODE_PREFIX = "cuisine_oac_"
OAUTH_CLIENT_ID_PREFIX = "cuisine_oc_"
OAUTH_CLIENT_SECRET_PREFIX = "cuisine_ocs_"
