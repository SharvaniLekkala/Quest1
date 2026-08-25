import logging
from time import perf_counter
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

logger = logging.getLogger(__name__)


class DialogueDetector:
    """Coordinates download, transcription, matching, exact seeking, and persistence."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.downloader = VideoDownloader(
            cookies_file=settings.cookies_file,
            cookies_from_browser=settings.cookies_from_browser,
            download_proxy=settings.download_proxy,
        )
        self.subtitles = SubtitleExtractor()
        self.transcriber = Transcriber(settings.whisper_model)
        self.matcher = DialogueMatcher(settings.match_threshold)
        self.frames = FrameExtractor()
        self.results = ResultBuilder()
        self.result_validator = ResultValidator()
        self.timestamps = TimestampResolver()
        self.vad = VoiceActivityFilter()

    def detect(self, request: DetectionRequest) -> DetectionResult:
        started_at = perf_counter()
        logger.info("[progress] Request received; validating video URL and dialogue.")
        validate_target(request.target)
        request = prepare_request(request)
        validate_public_video_url(str(request.video_url))
        job_directory = self.settings.output_dir / f"job_{uuid4().hex}"
        logger.info("[progress] Downloading video and available captions...")
        video_path = self.downloader.download(str(request.video_url), job_directory, self.settings.max_video_height)
        logger.info("[progress] Video download complete in %.1fs; reading captions.", perf_counter() - started_at)
        candidates = self.subtitles.extract(job_directory)
        candidates = self.vad.filter(candidates)
        match = self.matcher.best_match(request.target, candidates) if candidates else None

        # Captions can be missing or too weak. In either case, let Whisper
        # supply candidates before deciding whether the best available result is usable.
        if match is None or match.score < self.settings.match_threshold:
            logger.info("[progress] %s; transcribing audio with Whisper...", "No usable captions found" if match is None else "Caption match is below threshold")
            # Pass the video_path directly to Transcriber. This keeps audio and video
            # perfectly synchronized since PyAV/FFmpeg handle container edit lists properly.
            whisper_candidates = self.transcriber.transcribe(video_path)
            whisper_candidates = self.vad.filter(whisper_candidates)
            
            whisper_match = self.matcher.best_match(request.target, whisper_candidates)
            if match is None or whisper_match.score > match.score:
                match = whisper_match
        assert match is not None
        logger.info("[progress] Best dialogue match: %.1f%% (threshold %.1f%%).", match.score, self.settings.match_threshold)
        logger.info("[progress] Extracting the matching video frame...")
        frame_path = job_directory / "matched_frame.jpg"
        window = self.timestamps.resolve_window(match, request.target)
        frame_number = self.frames.extract(
            video_path,
            window.search_start,
            window.search_end,
            frame_path,
            anchor_seconds=window.anchor,
        )
        frame_url = f"/outputs/{job_directory.name}/{frame_path.name}"
        elapsed = perf_counter() - started_at
        result = self.results.build(
            match,
            frame_number,
            frame_url,
            timestamp_seconds=window.anchor,
            threshold=self.settings.match_threshold,
            processing_time_seconds=elapsed,
        )
        self.result_validator.validate(result, frame_path)
        result_path = job_directory / "result.json"
        write_json(result_path, result.model_dump())
        logger.info("[progress] Finished in %.1fs. Result saved to %s", elapsed, result_path)
        return result
