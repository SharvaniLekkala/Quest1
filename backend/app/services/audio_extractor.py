import subprocess
from pathlib import Path

from app.models.errors import PipelineError


class AudioExtractor:
    def extract_mono_wav(self, video_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", str(output_path)]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise PipelineError("FFmpeg could not extract audio from the video.")
        return output_path
