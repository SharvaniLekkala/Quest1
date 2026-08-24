from app.models.requests import DetectionRequest
from app.utils.text_utils import normalize_text


def prepare_request(request: DetectionRequest) -> DetectionRequest:
    """Trim user input while preserving the original URL and API model contract."""
    return DetectionRequest(video_url=request.video_url, target=" ".join(request.target.split()))


def target_terms(target: str) -> set[str]:
    return set(normalize_text(target).split())
