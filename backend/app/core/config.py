"""Application configuration loaded from backend/.env and environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Runtime settings.

    Field names are deliberately snake_case for Python. Pydantic settings reads
    the conventional uppercase environment equivalents, for example
    ``WHISPER_MODEL`` for ``whisper_model`` and ``OUTPUT_DIR`` for
    ``output_dir``.
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Video Dialogue Detector"
    app_version: str = "1.0.0"
    debug: bool = True

    output_dir: Path = PROJECT_DIR / "outputs"
    cookies_file: Path | None = None
    cookies_from_browser: str | None = None
    download_proxy: str | None = None
    whisper_model: str = "tiny"
    whisper_device: str = "auto"
    whisper_compute_type: str = "int8"

    match_threshold: float = 70.0
    semantic_match_threshold: float = 0.75
    max_video_height: int = 720

    enable_vad: bool = True
    enable_noise_reduction: bool = True
    enable_semantic_fallback: bool = True
    enable_subtitle_extraction: bool = True
    enable_speaker_diarization: bool = False


settings = Settings()
if not settings.output_dir.is_absolute():
    settings.output_dir = PROJECT_DIR / settings.output_dir
if settings.cookies_file and not settings.cookies_file.is_absolute():
    settings.cookies_file = BACKEND_DIR / settings.cookies_file
