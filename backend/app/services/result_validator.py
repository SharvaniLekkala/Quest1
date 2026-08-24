from pathlib import Path

from app.models.errors import PipelineError
from app.models.responses import DetectionResult


class ResultValidator:
    def validate(self, result: DetectionResult, image_path: Path) -> None:
        if result.frame_number < 0 or not result.extracted_text.strip():
            raise PipelineError("The generated result is incomplete.")
        if not image_path.is_file() or image_path.stat().st_size == 0:
            raise PipelineError("The generated frame image is missing or empty.")
