"""HTTP transport used by the generic media extractor.

Several public video hosts inspect TLS ClientHello fingerprints and drop
Python's default SSL handshake (``SSL: UNEXPECTED_EOF_WHILE_READING``).
When ``curl_cffi`` is installed, yt-dlp can impersonate a real browser for
every host — this is a transport capability, not a per-site integration.

Many public CDNs also reject the media URL unless the request looks like it
came from the watch page (HTTP 403). Referer/Origin are derived from the
submitted URL so this stays host-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}


def impersonate_targets() -> list[Any]:
    """Return available, generic browser TLS/client profiles."""
    try:
        import curl_cffi  # noqa: F401
        from yt_dlp.networking.impersonate import ImpersonateTarget
    except ImportError:
        logger.info(
            "Browser TLS impersonation is unavailable (install curl_cffi). "
            "Hosts that fingerprint TLS handshakes may refuse the connection."
        )
        return []
    targets = [
        ImpersonateTarget(client="chrome"),
        ImpersonateTarget(client="firefox"),
        ImpersonateTarget(client="edge"),
    ]
    # Some CDNs still accept an older Chrome JA3 after rejecting the newest.
    try:
        targets.append(ImpersonateTarget(client="chrome", version="110"))
    except TypeError:
        pass
    return targets


def transport_profiles() -> list[dict[str, Any]]:
    """Ordered HTTP client profiles to try for any host."""
    profiles: list[dict[str, Any]] = []
    for target in impersonate_targets():
        profiles.append({"impersonate": target})
    profiles.append({})
    return profiles


def origin_headers(page_url: str) -> dict[str, str]:
    """Browser-like Referer/Origin for the host of ``page_url``."""
    parsed = urlparse(page_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {}
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return {"Referer": f"{origin}/", "Origin": origin}


def apply_browser_headers(
    options: dict[str, Any],
    page_url: str | None = None,
    *,
    impersonating: bool = False,
) -> dict[str, Any]:
    merged = dict(options)
    headers = dict(merged.get("http_headers") or {})
    # Impersonation already sends a matching Chrome/Firefox header set.
    # Overriding Accept (and not UA) is a bot signal and often yields 403.
    if not impersonating:
        for key, value in _DEFAULT_HEADERS.items():
            headers.setdefault(key, value)
    if page_url:
        for key, value in origin_headers(page_url).items():
            headers.setdefault(key, value)
    if headers:
        merged["http_headers"] = headers
    return merged
