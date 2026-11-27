"""The uvicorn worker class gunicorn runs, with the server header off and
the proxy headers honoured for the trusted proxies only."""

from typing import Any
from typing import ClassVar

from uvicorn_worker import UvicornWorker


class CuisineUvicornWorker(UvicornWorker):
    CONFIG_KWARGS: ClassVar[dict[str, Any]] = {
        "server_header": False,
        "proxy_headers": True,
    }
