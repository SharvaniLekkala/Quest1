from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Project paths
    BASE_DIR: Path = Path(__file__).resolve().parents[3]
    DATA_DIR: Path = BASE_DIR / "data"
    JOBS_DIR: Path = DATA_DIR / "jobs"

    # Application
    APP_NAME: str = "Video Dialogue Detector"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Speech recognition
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # Matching
    FUZZY_MATCH_THRESHOLD: float = 80.0
    SEMANTIC_MATCH_THRESHOLD: float = 0.75

    # Processing
    ENABLE_VAD: bool = True
    ENABLE_NOISE_REDUCTION: bool = True
    ENABLE_SEMANTIC_FALLBACK: bool = True
    ENABLE_SUBTITLE_EXTRACTION: bool = True
    ENABLE_SPEAKER_DIARIZATION: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.JOBS_DIR.mkdir(parents=True, exist_ok=True)