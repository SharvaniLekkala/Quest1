from uuid import uuid4

from app.core.config import Settings
from app.models.requests import DetectionRequest
from app.models.responses import DetectionResult
from app.pipeline.preprocessing import prepare_request
from app.pipeline.validation import validate_public_video_url, validate_target
from app.services.dialogue_matcher import DialogueMatcher
from app.services.frame_extractor import FrameExtractor
from app.services.result_builder import ResultBuilder
from app.services.result_validator import ResultValidator
from app.services.subtitle_extractor import SubtitleExtractor
from app.services.transcriber import Transcriber
from app.services.timestamp_resolver import TimestampResolver
from app.services.vad import VoiceActivityFilter
from app.services.video_downloader import VideoDownloader
from app.utils.file_utils import write_json


class DialogueDetector:
    """Coordinates download, transcription, matching, exact seeking, and persistence."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.downloader = VideoDownloader()
        self.subtitles = SubtitleExtractor()
        self.transcriber = Transcriber(settings.whisper_model)
        self.matcher = DialogueMatcher(settings.match_threshold)
        self.frames = FrameExtractor()
        self.results = ResultBuilder()
        self.result_validator = ResultValidator()
        self.timestamps = TimestampResolver()
        self.vad = VoiceActivityFilter()

    def detect(self, request: DetectionRequest) -> DetectionResult:
        validate_target(request.target)
        request = prepare_request(request)
        validate_public_video_url(str(request.video_url))
        job_directory = self.settings.output_dir / f"job_{uuid4().hex}"
        video_path = self.downloader.download(str(request.video_url), job_directory, self.settings.max_video_height)
        candidates = self.subtitles.extract(job_directory)
        if not candidates:
            candidates = self.transcriber.transcribe(video_path)
        candidates = self.vad.filter(candidates)
        match = self.matcher.best_match(request.target, candidates)
        frame_path = job_directory / "matched_frame.jpg"
        frame_number = self.frames.extract(video_path, self.timestamps.resolve(match), frame_path)
        frame_url = f"/outputs/{job_directory.name}/{frame_path.name}"
        result = self.results.build(match, frame_number, frame_url)
        self.result_validator.validate(result, frame_path)
        result_path = job_directory / "result.json"
        write_json(result_path, result.model_dump())
        return result
