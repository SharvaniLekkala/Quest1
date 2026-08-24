import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioQuality:
    duration_seconds: float
    sample_rate: int


class AudioQualityAnalyzer:
    def analyze(self, wav_path: Path) -> AudioQuality:
        with wave.open(str(wav_path), "rb") as source:
            return AudioQuality(source.getnframes() / source.getframerate(), source.getframerate())
