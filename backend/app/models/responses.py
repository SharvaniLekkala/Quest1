from pydantic import BaseModel


class DetectionResult(BaseModel):
    timestamp: str
    frame_number: int
    extracted_text: str
    frame_image: str
