import hashlib
from pathlib import Path


class CacheManager:
    """Provides stable keys for future persistent-job or artifact caching."""

    def key(self, video_url: str, target: str) -> str:
        return hashlib.sha256(f"{video_url}\n{target}".encode("utf-8")).hexdigest()

    def result_path(self, cache_dir: Path, video_url: str, target: str) -> Path:
        return cache_dir / self.key(video_url, target) / "result.json"
