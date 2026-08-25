from pathlib import Path

from app.models.candidates import DialogueCandidate
from app.models.responses import DetectionResult
from app.utils.time_utils import format_timestamp


class ResultBuilder:
    def build(
        self,
        candidate: DialogueCandidate,
        frame_number: int,
        frame_image_url: str,
        timestamp_seconds: float | None = None,
        threshold: float = 0.0,
        processing_time_seconds: float = 0.0,
    ) -> DetectionResult:
        score = round(candidate.score, 1)
        if score >= 80:
            confidence = "high"
        elif score >= 60:
            confidence = "medium"
        else:
            confidence = "low"
        shown_at = candidate.start_seconds if timestamp_seconds is None else timestamp_seconds
        threshold_passed = candidate.score >= threshold
        caution = None
        if not threshold_passed:
            caution = (
                f"Best available match did not pass the configured {threshold:.0f}% threshold "
                "and may not be accurate."
            )
        return DetectionResult(
            timestamp=format_timestamp(max(0.0, shown_at)),
            frame_number=frame_number,
            extracted_text=candidate.text,
            frame_image=frame_image_url,
            score=score,
            confidence=confidence,
            threshold_passed=threshold_passed,
            caution=caution,
            processing_time_seconds=round(processing_time_seconds, 2),
        )
