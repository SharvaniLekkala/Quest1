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


def format_attempts(max_height: int) -> list[str]:
    """Strategies tried in order until a stream downloads successfully."""
    return [
        height_limited_formats(max_height),
        adaptive_stream_formats(max_height),
        "best",
    ]
