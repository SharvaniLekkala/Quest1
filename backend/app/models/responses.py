from pydantic import BaseModel


class DetectionResult(BaseModel):
    timestamp: str
    frame_number: int
    extracted_text: str
    frame_image: str
    score: float = 0.0
    confidence: str = "high"
