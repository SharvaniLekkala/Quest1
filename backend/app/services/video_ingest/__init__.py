"""Generic public-video ingestion.

Site-specific downloaders are intentionally avoided. Any publicly reachable
URL that a generic extractor (yt-dlp) can resolve is handled the same way.
"""

from app.services.video_ingest.ytdlp_extractor import YtdlpMediaExtractor

__all__ = ["YtdlpMediaExtractor"]
