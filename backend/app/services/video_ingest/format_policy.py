"""Protocol-agnostic format selection for public video streams."""

from __future__ import annotations


def height_limited_formats(max_height: int) -> str:
    """Prefer separate or muxed streams at or below ``max_height``."""
    height = int(max_height)
    return (
        f"bv*[height<={height}]+ba/"
        f"b[height<={height}]/"
        f"best[height<={height}]/"
        "best"
    )


def adaptive_stream_formats(max_height: int) -> str:
    """Prefer HLS/DASH when progressive HTTP downloads are rejected (HTTP 403)."""
    height = int(max_height)
    return (
        f"bv*[height<={height}][protocol^=m3u8]+ba/"
        f"b[height<={height}][protocol^=m3u8]/"
        f"bv*[height<={height}][protocol^=http]+ba/"
        f"best[protocol^=m3u8]/"
        "best"
    )


def progressive_formats(max_height: int) -> str:
    """Single muxed files — some CDNs 403 separate video+audio or HLS fragments."""
    height = int(max_height)
    return (
        f"b[height<={height}][ext=mp4]/"
        f"b[height<={height}]/"
        f"best[ext=mp4]/"
        "best"
    )


def format_attempts(max_height: int, *, prefer_adaptive: bool = False) -> list[str]:
    """Strategies tried in order until a stream downloads successfully."""
    attempts = [
        height_limited_formats(max_height),
        adaptive_stream_formats(max_height),
        progressive_formats(max_height),
        "best",
    ]
    if prefer_adaptive:
        # OK.ru commonly exposes signed HLS media. Trying it first avoids
        # spending time on progressive variants the CDN may reject with 403.
        attempts.remove(adaptive_stream_formats(max_height))
        attempts.insert(0, adaptive_stream_formats(max_height))
    return attempts
