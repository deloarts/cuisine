"""
Jinja rendering of mail templates. Administrator-authored text runs in a
sandboxed environment with autoescaping on, so a value such as a user's
name can never inject markup. The packaged `<kind>.<locale>.html` files are
the defaults; their `<title>` is the subject. Adapted from glados.
"""

import re
from pathlib import Path
from typing import Any

from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment

from src.platform.domain.value_objects.mail import MailTemplateKind

TEMPLATES_DIR = Path(__file__).parent / "templates"
_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class JinjaMailRenderer:
    def __init__(self) -> None:
        self._env = SandboxedEnvironment(autoescape=True)

    def render(self, source: str, context: dict[str, Any]) -> str:
        try:
            return self._env.from_string(source).render(**context)
        except TemplateError as exc:
            raise ValueError(f"The template does not render: {exc}") from exc

    def packaged(self, kind: MailTemplateKind, locale: str) -> tuple[str, str] | None:
        path = TEMPLATES_DIR / f"{kind.value}.{locale}.html"
        if not path.is_file():
            return None
        body = path.read_text(encoding="utf-8")
        match = _TITLE.search(body)
        return (match.group(1).strip() if match else ""), body
