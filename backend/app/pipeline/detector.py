from uuid import uuid4

from app.core.config import Settings
from app.models.requests import DetectionRequest
from app.models.responses import DetectionResult
from app.pipeline.preprocessing import prepare_request
from app.pipeline.validation import validate_public_video_url, validate_target
from app.services.audio_enhancer import AudioEnhancer
from app.services.audio_extractor import AudioExtractor
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
        self.audio_extractor = AudioExtractor()
        self.audio_enhancer = AudioEnhancer()

    def detect(self, request: DetectionRequest) -> DetectionResult:
        validate_target(request.target)
        request = prepare_request(request)
        validate_public_video_url(str(request.video_url))
        job_directory = self.settings.output_dir / f"job_{uuid4().hex}"
        video_path = self.downloader.download(str(request.video_url), job_directory, self.settings.max_video_height)
        candidates = self.subtitles.extract(job_directory)
        if not candidates:
            # Extract mono 16 kHz wav from the video, optionally denoise it,
            # then run Whisper on the cleaned audio for better accuracy.
            wav_path = self.audio_extractor.extract_mono_wav(
                video_path, job_directory / "audio.wav"
            )
            if self.settings.enable_noise_reduction:
                wav_path = self.audio_enhancer.enhance(wav_path)
            candidates = self.transcriber.transcribe(wav_path)
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
