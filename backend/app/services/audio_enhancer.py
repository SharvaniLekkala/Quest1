from pathlib import Path


class AudioEnhancer:
    """Extension point for denoising; preserves audio when no DSP model is configured."""

    def enhance(self, audio_path: Path) -> Path:
        return audio_path
