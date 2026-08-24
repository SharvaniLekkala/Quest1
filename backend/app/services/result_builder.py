from pathlib import Path

from app.models.candidates import DialogueCandidate
from app.models.responses import DetectionResult
from app.utils.time_utils import format_timestamp


class ResultBuilder:
    def build(self, candidate: DialogueCandidate, frame_number: int, frame_image_url: str) -> DetectionResult:
        return DetectionResult(
            timestamp=format_timestamp(candidate.start_seconds),
            frame_number=frame_number,
            extracted_text=candidate.text,
            frame_image=frame_image_url,
        )
