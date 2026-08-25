"""HTTP transport used by the generic media extractor.

Several public video hosts inspect TLS ClientHello fingerprints and drop
Python's default SSL handshake (``SSL: UNEXPECTED_EOF_WHILE_READING``).
When ``curl_cffi`` is installed, yt-dlp can impersonate a real browser for
every host — this is a transport capability, not a per-site integration.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Browser-like headers applied on every request. User-Agent is left to the
# impersonation backend when it is available so the JA3/JA4 fingerprint and
# header set stay consistent.
_DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def impersonate_targets() -> list[Any]:
    """Return available, generic browser TLS/client profiles.

    Some hosts accept one real browser fingerprint but reset another. Trying
    more than one standard browser client gives every supported source the
    same transport fallback without adding provider-specific extractors.
    """
    try:
        import curl_cffi  # noqa: F401
        from yt_dlp.networking.impersonate import ImpersonateTarget
    except ImportError:
        logger.info(
            "Browser TLS impersonation is unavailable (install curl_cffi). "
            "Hosts that fingerprint TLS handshakes may refuse the connection."
        )
        return []
    # Do not pin a historical browser version here.  A fingerprint such as
    # Edge 101 (from 2022) can itself be a bot signal and can be unavailable
    # in newer curl_cffi builds.  Let yt-dlp select the newest profile that
    # the installed curl_cffi supports, then fall back to other current
    # browser families.
    return [
        ImpersonateTarget(client="chrome"),
        ImpersonateTarget(client="firefox"),
        ImpersonateTarget(client="edge"),
    ]


def transport_profiles() -> list[dict[str, Any]]:
    """Ordered HTTP client profiles to try for any host.

    Impersonation is preferred because it matches a normal browser. A plain
    Python TLS profile remains as a fallback for hosts or environments where
    curl_cffi is missing or fails.
    """
    profiles: list[dict[str, Any]] = []
    for target in impersonate_targets():
        profiles.append({"impersonate": target})
    profiles.append({})
    return profiles


def apply_browser_headers(options: dict[str, Any]) -> dict[str, Any]:
    merged = dict(options)
    headers = dict(_DEFAULT_HEADERS)
    headers.update(merged.get("http_headers") or {})
    merged["http_headers"] = headers
    return merged
