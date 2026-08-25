"""yt-dlp backed extractor used for any public video URL."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from shutil import which
from typing import Any
from urllib.parse import urlparse

import yt_dlp

from app.models.errors import PipelineError
from app.services.video_ingest.format_policy import format_attempts
from app.services.video_ingest.transport import apply_browser_headers, transport_profiles

logger = logging.getLogger(__name__)

_TRANSIENT_ERRORS = (
    "WinError 10054",
    "WinError 10053",
    "Connection reset by peer",
    "TransportError",
    "forcibly closed",
)
_FINGERPRINT_ERRORS = (
    "UNEXPECTED_EOF_WHILE_READING",
    "SSL_ERROR_SYSCALL",
)
_FORBIDDEN_MARKERS = ("HTTP Error 403", "403: Forbidden", "access denied")
_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 5


class DownloadProgressReporter:
    """Emit bounded download updates through the application console logger."""

    def __init__(self) -> None:
        self._last_report_at = 0.0

    def __call__(self, update: dict[str, Any]) -> None:
        status = update.get("status")
        if status == "finished":
            logger.info("[progress] Media download complete; finalizing file...")
            return
        if status != "downloading":
            return
        now = time.monotonic()
        if now - self._last_report_at < 3:
            return
        self._last_report_at = now
        logger.info(
            "[progress] Downloading media: %s at %s (ETA %s)",
            str(update.get("_percent_str") or "unknown").strip(),
            str(update.get("_speed_str") or "unknown").strip(),
            str(update.get("_eta_str") or "unknown").strip(),
        )


class YtdlpMediaExtractor:
    """Download a single public video (and optional captions) via yt-dlp."""

    def download_video(
        self,
        url: str,
        destination: Path,
        max_height: int,
        extra_options: dict[str, Any] | None = None,
    ) -> None:
        extra = extra_options or {}
        logger.info("[progress] Resolving public video page: %s", url)
        last_error: Exception | None = None
        tried_impersonate = False

        for native_hls in (True, False):
            for profile in transport_profiles():
                if "impersonate" in profile:
                    tried_impersonate = True
                for format_selector in format_attempts(
                    max_height,
                    prefer_adaptive=self._prefers_adaptive_stream(url),
                ):
                    options = self._video_options(destination, format_selector)
                    options.update(profile)
                    options.update(extra)
                    options["hls_prefer_native"] = native_hls
                    options = apply_browser_headers(
                        options,
                        url,
                        impersonating="impersonate" in options,
                    )
                    try:
                        self._download_with_retry(url, options, "video")
                        return
                    except Exception as error:
                        last_error = error
                        if self._should_try_next_format(error):
                            logger.info(
                                "Stream download rejected (%s); trying the next format policy.",
                                error,
                            )
                            continue
                        if self._should_try_next_transport(error):
                            logger.info(
                                "HTTP transport failed (%s); trying the next client profile.",
                                error,
                            )
                            break
                        raise self._to_pipeline_error(error, tried_impersonate) from error

        assert last_error is not None
        raise self._to_pipeline_error(last_error, tried_impersonate) from last_error

    def download_subtitles(
        self,
        url: str,
        destination: Path,
        extra_options: dict[str, Any] | None = None,
    ) -> None:
        extra = extra_options or {}
        last_error: Exception | None = None
        for profile in transport_profiles():
            options = self._subtitle_options(destination)
            options.update(profile)
            options.update(extra)
            options = apply_browser_headers(
                options,
                url,
                impersonating="impersonate" in options,
            )
            try:
                with yt_dlp.YoutubeDL(options) as downloader:
                    downloader.extract_info(url, download=True)
                return
            except Exception as error:
                last_error = error
                if self._should_try_next_transport(error):
                    continue
                logger.info("Captions unavailable; using transcription fallback: %s", error)
                return
        logger.info("Captions unavailable; using transcription fallback: %s", last_error)

    def _download_with_retry(self, url: str, options: dict[str, Any], label: str) -> None:
        last_error: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                logger.info("[progress] Starting %s download (attempt %d/%d).", label, attempt, _MAX_ATTEMPTS)
                with yt_dlp.YoutubeDL(options) as downloader:
                    downloader.extract_info(url, download=True)
                return
            except Exception as error:
                last_error = error
                if self._is_transient(error) and attempt < _MAX_ATTEMPTS:
                    wait = _BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        "Transient %s download error (attempt %d/%d), retrying in %ds: %s",
                        label,
                        attempt,
                        _MAX_ATTEMPTS,
                        wait,
                        error,
                    )
                    time.sleep(wait)
                    continue
                break
        assert last_error is not None
        raise last_error

    def _video_options(self, destination: Path, format_selector: str) -> dict[str, Any]:
        options = self._common_network_options()
        options.update(
            {
                "format": format_selector,
                "ffmpeg_location": self._ffmpeg_location(),
                "outtmpl": str(destination / "source.%(ext)s"),
            }
        )
        return options

    def _subtitle_options(self, destination: Path) -> dict[str, Any]:
        options = self._common_network_options()
        options.update(
            {
                "outtmpl": str(destination / "source.%(ext)s"),
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitlesformat": "vtt",
                "subtitleslangs": ["en", "en-US", "en-.*"],
                "ignoreerrors": True,
            }
        )
        return options

    @staticmethod
    def _common_network_options() -> dict[str, Any]:
        options: dict[str, Any] = {
            "noplaylist": True,
            "retries": 5,
            "extractor_retries": 5,
            "fragment_retries": 5,
            "socket_timeout": 60,
            "sleep_interval_requests": 2,
            "nocheckcertificate": True,
            # HLS URLs are frequently signed for the browser-like HTTP session
            # that resolved the watch page. Native yt-dlp HLS keeps fragment
            # requests in that transport; FFmpeg launches a separate client
            # and can be rejected by otherwise public hosts. This applies to
            # the HLS protocol, not to a particular video website.
            "hls_prefer_native": True,
            "progress_hooks": [DownloadProgressReporter()],
            "noprogress": True,
            "quiet": True,
            "no_warnings": True,
        }
        return options

    @staticmethod
    def _ffmpeg_location() -> str:
        system_ffmpeg = which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as error:
            raise PipelineError(
                "FFmpeg is required to combine this provider's video and audio streams. "
                "Install backend requirements or install FFmpeg on PATH."
            ) from error

    @staticmethod
    def _prefers_adaptive_stream(url: str) -> bool:
        """Prefer signed HLS for OK.ru public watch links."""
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        return host == "ok.ru" or host.endswith(".ok.ru")

    @staticmethod
    def _is_transient(error: Exception) -> bool:
        message = str(error)
        return any(fragment in message for fragment in _TRANSIENT_ERRORS)

    @staticmethod
    def _is_fingerprint(error: Exception) -> bool:
        message = str(error)
        return any(fragment in message for fragment in _FINGERPRINT_ERRORS)

    @classmethod
    def _should_try_next_format(cls, error: Exception) -> bool:
        message = str(error)
        if any(marker in message for marker in _FORBIDDEN_MARKERS):
            return True
        lowered = message.lower()
        return "requested format is not available" in lowered

    @classmethod
    def _should_try_next_transport(cls, error: Exception) -> bool:
        message = str(error)
        if cls._is_transient(error) or cls._is_fingerprint(error):
            return True
        lowered = message.lower()
        return (
            "impersonate" in lowered
            or "curl_cffi" in lowered
            or "ssl" in lowered
        )

    @classmethod
    def _to_pipeline_error(cls, error: Exception, tried_impersonate: bool) -> PipelineError:
        message = str(error)
        lowered = message.lower()

        if cls._is_fingerprint(error) and not tried_impersonate:
            return PipelineError(
                "The video host closed the TLS connection before the page could be read. "
                "This is usually TLS fingerprinting of automated clients. Install the "
                "curl_cffi package so the downloader can use a browser-like HTTP client, "
                "then retry."
            )
        if cls._is_fingerprint(error) or cls._is_transient(error):
            return PipelineError(
                "The video host closed the TLS connection before serving the page, even "
                "after trying current browser TLS profiles. This is a provider or network "
                "block, not a certificate error; disabling certificate checks or retrying "
                "will not bypass it. Confirm the URL opens in a normal browser on this "
                "network, remove any untrusted DOWNLOAD_PROXY, then retry later or from "
                "a network where the public page is available."
            )
        if any(marker in message for marker in _FORBIDDEN_MARKERS):
            return PipelineError(
                "The video host returned HTTP 403 Forbidden for the media stream. "
                "The video may be region-locked, require a logged-in session, or block "
                "automated downloads of that format."
            )
        if "unsupported url" in lowered:
            return PipelineError(
                "This URL is not recognized as a public video page by the generic extractor. "
                "Use a direct, publicly accessible watch URL (not a local file or private link)."
            )
        if any(token in lowered for token in ("private video", "login required", "sign in", "join this channel")):
            return PipelineError("This video is not publicly accessible.")
        return PipelineError(f"Could not download the public video: {error}")
