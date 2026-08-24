from pathlib import Path

import yt_dlp

from app.models.errors import PipelineError

class VideoDownloader:
    """Downloads a public video to a dedicated job directory."""

    def download(self, url: str, destination: Path, max_height: int) -> Path:
        destination.mkdir(parents=True, exist_ok=True)
        options = {
            "format": f"bv*[height<={max_height}]+ba/b[height<={max_height}]/b",
            "outtmpl": str(destination / "source.%(ext)s"),
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "vtt",
            "subtitleslangs": ["all"],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                downloader.extract_info(url, download=True)
        except Exception as error:
            raise PipelineError(f"Could not download the public video: {error}") from error
        video_extensions = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}
        videos = [path for path in destination.glob("source.*") if path.suffix.lower() in video_extensions]
        if not videos:
            raise PipelineError("Video download completed without creating a media file.")
        return max(videos, key=lambda path: path.stat().st_size)
