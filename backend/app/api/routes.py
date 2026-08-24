from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.models.errors import PipelineError
from app.models.requests import DetectionRequest
from app.models.responses import DetectionResult
from app.pipeline.detector import DialogueDetector

router = APIRouter(prefix="/api/v1", tags=["dialogue detection"])
detector = DialogueDetector(settings)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/detect", response_model=DetectionResult, status_code=status.HTTP_201_CREATED)
def detect_dialogue(request: DetectionRequest) -> DetectionResult:
    try:
        return detector.detect(request)
    except PipelineError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
