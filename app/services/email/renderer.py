"""
Email template renderer using Jinja2.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

TEMPLATES_DIR = Path(__file__).parent / "templates"

_env: Environment | None = None


def get_template_env() -> Environment:
    """Get or create Jinja2 environment."""
    global _env
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _env


def render_template(template_name: str, data: dict[str, Any]) -> str:
    """
    Render an email template with the given data.

    Args:
        template_name: Template name without extension (e.g., "welcome")
        data: Template variables

    Returns:
        Rendered HTML string
    """
    env = get_template_env()

    template_file = f"{template_name}.html"
    template = env.get_template(template_file)

    context = {
        "app_name": settings.PROJECT_NAME,
        "year": datetime.now().year,
        "unsubscribe_url": "#",
        "privacy_url": "#",
        **data,
    }

    return template.render(**context)


def render_text_fallback(html_content: str) -> str:
    """
    Generate plain text fallback from HTML.
    Simple conversion that strips HTML tags.
    """
    import re

    text = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = text.strip()

    return text
