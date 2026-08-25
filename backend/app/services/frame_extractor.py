import logging
from pathlib import Path

import cv2
import numpy as np

from app.models.errors import PipelineError

logger = logging.getLogger(__name__)

_SAMPLE_COUNT = 11
_CUT_DIFF = 22.0
_BOTTOM_CAPTION_RATIO = 0.18


class FrameExtractor:
    """Select a representative in-speech frame from a timestamp window.

    Whisper/subtitle times are treated as a search center, not an exact index.
    Scoring prefers temporal alignment with speech, scene stability (avoiding
    cuts/transitions), and sharpness on the picture area rather than captions.
    """

    def extract(
        self,
        video_path: Path,
        start_seconds: float,
        end_seconds: float | Path,
        output_path: Path | None = None,
        *,
        anchor_seconds: float | None = None,
    ) -> int:
        # Backward compatibility: (video_path, timestamp_seconds, output_path)
        if isinstance(end_seconds, (Path, str)) or output_path is None:
            real_output_path = Path(end_seconds)
            search_start = float(start_seconds)
            search_end = search_start + 1.0
            anchor = search_start if anchor_seconds is None else float(anchor_seconds)
        else:
            search_start = float(start_seconds)
            search_end = float(end_seconds)
            real_output_path = output_path
            if search_end < search_start:
                search_start, search_end = search_end, search_start
            mid = (search_start + search_end) / 2.0
            anchor = mid if anchor_seconds is None else float(anchor_seconds)

        capture = cv2.VideoCapture(str(video_path))
        try:
            if not capture.isOpened():
                raise PipelineError("OpenCV could not open the downloaded video.")

            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            if fps <= 1e-3:
                fps = 25.0
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            duration = frame_count / fps if frame_count > 0 else search_end + 1.0

            search_start = min(max(0.0, search_start), max(0.0, duration - 1.0 / fps))
            search_end = min(max(search_start + 1.0 / fps, search_end), duration)
            anchor = min(max(search_start, anchor), search_end)

            samples = self._sample_frames(capture, search_start, search_end, fps)
            picked = self._select_frame(samples, anchor, search_start, search_end)

            if picked is None:
                picked = self._fallback_frame(capture, anchor, search_start)
            if picked is None:
                raise PipelineError("Could not decode any frame in the dialogue segment.")

            frame_number, _time, frame = picked
            real_output_path.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(real_output_path), frame):
                raise PipelineError("Could not write the extracted image.")
            return frame_number
        finally:
            capture.release()

    def _sample_frames(
        self,
        capture: cv2.VideoCapture,
        search_start: float,
        search_end: float,
        fps: float,
    ) -> list[tuple[int, float, np.ndarray]]:
        times = np.linspace(search_start, search_end, num=_SAMPLE_COUNT)
        samples: list[tuple[int, float, np.ndarray]] = []
        seen: set[int] = set()
        for t in times:
            index = int(round(float(t) * fps))
            index = max(0, index)
            if index in seen:
                continue
            seen.add(index)
            # Frame-index seek is more stable than CAP_PROP_POS_MSEC on long
            # videos, VFR streams, and fragmented MP4 downloads.
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            success, frame = capture.read()
            if not success or frame is None:
                capture.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000.0)
                success, frame = capture.read()
                if not success or frame is None:
                    continue
            actual_index = int(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            if actual_index < 0:
                actual_index = index
            actual_time = actual_index / fps
            samples.append((actual_index, actual_time, frame))
        return samples

    def _select_frame(
        self,
        samples: list[tuple[int, float, np.ndarray]],
        anchor: float,
        search_start: float,
        search_end: float,
    ) -> tuple[int, float, np.ndarray] | None:
        if not samples:
            return None

        grays = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) for _, _, frame in samples]
        diffs = [0.0]
        for prev, cur in zip(grays, grays[1:]):
            if prev.shape != cur.shape:
                diffs.append(999.0)
            else:
                diffs.append(float(np.mean(cv2.absdiff(prev, cur))))

        scene_ids = [0]
        for diff in diffs[1:]:
            scene_ids.append(scene_ids[-1] + (1 if diff > _CUT_DIFF else 0))

        anchor_index = int(np.argmin([abs(t - anchor) for _, t, _ in samples]))
        preferred_scene = scene_ids[anchor_index]

        sigma = max(0.22, 0.28 * (search_end - search_start))
        best_i = -1
        best_score = -1.0

        for i, (_idx, time, frame) in enumerate(samples):
            gray = grays[i]
            brightness = float(np.mean(gray))
            if brightness < 8 or brightness > 248:
                continue

            picture = gray[: max(1, int(gray.shape[0] * (1.0 - _BOTTOM_CAPTION_RATIO))), :]
            sharpness = float(cv2.Laplacian(picture, cv2.CV_64F).var())

            prev_diff = diffs[i] if i > 0 else 0.0
            next_diff = diffs[i + 1] if i + 1 < len(diffs) else 0.0
            neighbor = max(prev_diff, next_diff)
            stability = 1.0 / (1.0 + neighbor / 12.0)

            temporal = float(np.exp(-0.5 * ((time - anchor) / sigma) ** 2))
            scene_weight = 1.0 if scene_ids[i] == preferred_scene else 0.18
            # Softly keep usable dark music-video frames instead of dropping them.
            brightness_weight = 1.0
            if brightness < 22:
                brightness_weight = 0.55
            elif brightness > 230:
                brightness_weight = 0.5

            score = (
                (np.log1p(sharpness) + 1.0)
                * (0.35 + 0.65 * temporal)
                * (0.4 + 0.6 * stability)
                * scene_weight
                * brightness_weight
            )
            if score > best_score:
                best_score = score
                best_i = i

        if best_i < 0:
            return samples[anchor_index]
        return samples[best_i]

    def _fallback_frame(
        self,
        capture: cv2.VideoCapture,
        anchor: float,
        search_start: float,
    ) -> tuple[int, float, np.ndarray] | None:
        for t in (anchor, search_start):
            capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
            success, frame = capture.read()
            if success and frame is not None:
                frame_number = int(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                return max(frame_number, 0), t, frame
        return None
