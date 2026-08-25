import logging
from pathlib import Path

from app.models.errors import PipelineError
from app.services.video_ingest import YtdlpMediaExtractor

logger = logging.getLogger(__name__)

_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}


class VideoDownloader:
    """Job-facing facade over the generic public-video extractor."""

    def __init__(
        self,
        cookies_file: Path | None = None,
        cookies_from_browser: str | None = None,
        download_proxy: str | None = None,
    ) -> None:
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser
        self.download_proxy = download_proxy
        self._extractor = YtdlpMediaExtractor()

    def download(self, url: str, destination: Path, max_height: int) -> Path:
        destination.mkdir(parents=True, exist_ok=True)
        selected_options: dict | None = None
        last_error: PipelineError | None = None
        for options in self._transport_option_candidates():
            try:
                self._extractor.download_video(url, destination, max_height, options)
                selected_options = options
                break
            except PipelineError as error:
                last_error = error
                logger.info("Video transport path failed: %s", error)
        if selected_options is None:
            assert last_error is not None
            raise last_error

        videos = [
            path
            for path in destination.glob("source.*")
            if path.suffix.lower() in _VIDEO_EXTENSIONS
        ]
        if not videos:
            raise PipelineError("Video download completed without creating a media file.")

        try:
            self._extractor.download_subtitles(url, destination, selected_options)
        except Exception as error:
            logger.info("Captions unavailable; using transcription fallback: %s", error)

        return max(videos, key=lambda path: path.stat().st_size)

    def _transport_options(self) -> dict:
        """Optional generic network settings for public video requests."""
        options: dict = {}
        if self.cookies_file is not None:
            if not self.cookies_file.is_file():
                raise PipelineError(
                    "COOKIES_FILE is configured but the cookies file does not exist."
                )
            logger.info("Using cookies file at: %s", self.cookies_file)
            options["cookiefile"] = str(self.cookies_file)
        elif self.cookies_from_browser:
            logger.info(
                "Reading cookies directly from browser: %s "
                "(make sure %s is fully CLOSED)",
                self.cookies_from_browser,
                self.cookies_from_browser,
            )
            options["cookiesfrombrowser"] = (self.cookies_from_browser,)

        if self.download_proxy:
            options["proxy"] = self.download_proxy
        return options

    def _transport_option_candidates(self) -> list[dict]:
        """Try the normal route before an explicitly configured proxy route."""
        configured = self._transport_options()
        proxy = configured.pop("proxy", None)
        candidates = [configured]
        if proxy:
            candidates.append({**configured, "proxy": proxy})
        return candidates
