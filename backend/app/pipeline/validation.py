import ipaddress
from urllib.parse import urlparse

from app.models.errors import PipelineError


def validate_public_video_url(url: str) -> None:
    """Reject malformed or local URLs before passing them to a downloader."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise PipelineError("video_url must be an absolute HTTP(S) URL.")
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        raise PipelineError("Local URLs are not accepted.")
    try:
        address = ipaddress.ip_address(parsed.hostname or "")
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise PipelineError("Private or reserved network addresses are not accepted.")
    except ValueError:
        # Host names are resolved by the approved downloader. Deployments that
        # accept untrusted users should additionally enforce a domain allow-list.
        pass


def validate_target(target: str) -> None:
    if not target.strip():
        raise PipelineError("target must contain dialogue text, not only whitespace.")
