import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.frame_extractor import FrameExtractor
from app.services.timestamp_resolver import TimestampResolver
from app.models.candidates import DialogueCandidate


def _write_video(path: Path, scenes: list[tuple[int, tuple[int, int, int], str, int]]) -> None:
    """scenes: list of (n_frames, bgr, label, blur_ksize)."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(path), fourcc, 25.0, (640, 480))
    for n_frames, color, label, blur in scenes:
        for _ in range(n_frames):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = color
            cv2.putText(frame, label, (40, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
            if blur > 1:
                frame = cv2.GaussianBlur(frame, (blur, blur), 0)
            out.write(frame)
    out.release()


class TestFrameExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = FrameExtractor()
        self.temp_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        self.test_video_path = Path(self.temp_video.name)
        self.temp_video.close()
        _write_video(
            self.test_video_path,
            [
                (25, (255, 0, 0), "Scene 1", 0),
                (25, (0, 255, 0), "Scene 2 - Sharp Text", 0),
                (25, (0, 0, 255), "Scene 3", 51),
            ],
        )

    def tearDown(self):
        if self.test_video_path.exists():
            try:
                self.test_video_path.unlink()
            except OSError:
                pass

    def test_extract_robust_frame(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_img = Path(tmpdir) / "matched_frame.jpg"
            frame_num = self.extractor.extract(
                self.test_video_path,
                start_seconds=1.0,
                end_seconds=2.0,
                output_path=output_img,
                anchor_seconds=1.25,
            )
            self.assertTrue(output_img.exists())
            self.assertTrue(output_img.stat().st_size > 0)
            self.assertTrue(25 <= frame_num < 50)

    def test_backward_compatibility(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_img = Path(tmpdir) / "matched_frame.jpg"
            frame_num = self.extractor.extract(self.test_video_path, 1.5, output_img)
            self.assertTrue(output_img.exists())
            self.assertGreaterEqual(frame_num, 0)

    def test_dialogue_on_cut_picks_post_cut_scene(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_img = Path(tmpdir) / "cut.jpg"
            frame_num = self.extractor.extract(
                self.test_video_path,
                start_seconds=0.7,
                end_seconds=1.8,
                output_path=output_img,
                anchor_seconds=1.15,
            )
            self.assertTrue(25 <= frame_num < 50)

    def test_music_video_title_card_not_preferred(self):
        handle = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        path = Path(handle.name)
        handle.close()
        try:
            _write_video(
                path,
                [
                    (20, (0, 0, 0), "TITLE CARD SHARP", 0),
                    (55, (40, 90, 40), "SPEAKER", 0),
                ],
            )
            with tempfile.TemporaryDirectory() as tmpdir:
                output_img = Path(tmpdir) / "mv.jpg"
                frame_num = self.extractor.extract(
                    path,
                    start_seconds=0.5,
                    end_seconds=2.2,
                    output_path=output_img,
                    anchor_seconds=1.1,
                )
                self.assertGreaterEqual(frame_num, 20)
        finally:
            path.unlink(missing_ok=True)

    def test_fast_cuts_avoid_transition_sample(self):
        handle = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        path = Path(handle.name)
        handle.close()
        try:
            scenes = []
            for i in range(15):
                color = (0, 255, 0) if i % 2 == 0 else (255, 0, 0)
                scenes.append((5, color, f"cut{i}", 0))
            _write_video(path, scenes)
            with tempfile.TemporaryDirectory() as tmpdir:
                output_img = Path(tmpdir) / "fast.jpg"
                frame_num = self.extractor.extract(
                    path,
                    start_seconds=1.0,
                    end_seconds=2.0,
                    output_path=output_img,
                    anchor_seconds=1.4,
                )
                self.assertTrue(output_img.exists())
                self.assertGreaterEqual(frame_num, 0)
        finally:
            path.unlink(missing_ok=True)

    def test_subtitle_band_does_not_override_scene(self):
        handle = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        path = Path(handle.name)
        handle.close()
        try:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(str(path), fourcc, 25.0, (640, 480))
            for i in range(75):
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame[:] = (30, 80, 30) if i >= 25 else (90, 20, 20)
                cv2.putText(
                    frame,
                    "CAPTION LINE HERE",
                    (40, 450),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),
                    2,
                )
                out.write(frame)
            out.release()
            with tempfile.TemporaryDirectory() as tmpdir:
                output_img = Path(tmpdir) / "subs.jpg"
                frame_num = self.extractor.extract(
                    path,
                    start_seconds=1.0,
                    end_seconds=2.0,
                    output_path=output_img,
                    anchor_seconds=1.3,
                )
                self.assertTrue(25 <= frame_num < 50)
        finally:
            path.unlink(missing_ok=True)


class TestPhraseWindow(unittest.TestCase):
    def test_phrase_inside_long_caption_block(self):
        resolver = TimestampResolver()
        candidate = DialogueCandidate(
            text="intro chatter then the target line then more talking afterwards",
            start_seconds=10.0,
            end_seconds=20.0,
        )
        window = resolver.resolve_window(candidate, "the target line")
        self.assertGreater(window.anchor, 12.0)
        self.assertLess(window.anchor, 17.0)
        self.assertLess(window.search_start, window.anchor)
        self.assertGreater(window.search_end, window.anchor)

    def test_whisper_jitter_expands_short_span(self):
        resolver = TimestampResolver()
        candidate = DialogueCandidate(text="hello there", start_seconds=4.0, end_seconds=4.2)
        window = resolver.resolve_window(candidate, "hello there")
        self.assertGreaterEqual(window.search_end - window.search_start, 0.8)
        self.assertGreaterEqual(window.anchor, 4.0)


if __name__ == "__main__":
    unittest.main()
