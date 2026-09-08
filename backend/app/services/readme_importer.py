import re
from urllib.parse import urlparse

from pydantic import HttpUrl, TypeAdapter, ValidationError

from app.schemas import LinkPreview, ResourceCategory


MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
BARE_URL_RE = re.compile(r"(?<!\()https?://[^\s<>)\"']+")
URL_ADAPTER = TypeAdapter(HttpUrl)


def extract_links_from_markdown(markdown: str) -> list[LinkPreview]:
    links: dict[str, LinkPreview] = {}

    for label, raw_url in MARKDOWN_LINK_RE.findall(markdown):
        _add_link(links, label.strip(), raw_url.strip())

    for raw_url in BARE_URL_RE.findall(markdown):
        _add_link(links, _label_from_url(raw_url), raw_url.strip())

    return list(links.values())


def _add_link(links: dict[str, LinkPreview], label: str, raw_url: str) -> None:
    url = raw_url.rstrip(".,")
    try:
        parsed_url = URL_ADAPTER.validate_python(url)
    except ValidationError:
        return

    normalized = str(parsed_url)
    links.setdefault(
        normalized,
        LinkPreview(
            name=(label or _label_from_url(normalized))[:120],
            url=parsed_url,
            category=_category_for_url(normalized),
        ),
    )


def _label_from_url(url: str) -> str:
    host = urlparse(url).hostname or url
    return host.replace("www.", "")


def _category_for_url(url: str) -> ResourceCategory:
    host = (urlparse(url).hostname or "").lower()
    if "github.com" in host:
        return ResourceCategory.github
    if "linkedin.com" in host or "x.com" in host or "twitter.com" in host:
        return ResourceCategory.social
    if "coursera.org" in host or "credly.com" in host or "udemy.com" in host:
        return ResourceCategory.certificate
    return ResourceCategory.project
