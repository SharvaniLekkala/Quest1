from pathlib import Path

from app.models.candidates import DialogueCandidate
from app.models.errors import PipelineError


class Transcriber:
    """Lazy-loads faster-whisper only if the video has no usable subtitles."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def transcribe(self, video_path: Path) -> list[DialogueCandidate]:
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel(self.model_name, device="auto", compute_type="int8")
            segments, _ = model.transcribe(str(video_path), vad_filter=True, word_timestamps=True)
            return [DialogueCandidate(segment.text.strip(), segment.start, segment.end) for segment in segments if segment.text.strip()]
        except Exception as error:
            raise PipelineError(f"Transcription failed. Ensure FFmpeg is installed: {error}") from error
