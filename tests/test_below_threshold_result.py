import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.candidates import DialogueCandidate
from app.services.dialogue_matcher import DialogueMatcher
from app.services.result_builder import ResultBuilder


class TestBelowThresholdResult(unittest.TestCase):
    def test_matcher_keeps_the_best_candidate_below_threshold(self):
        candidate = DialogueCandidate("unrelated dialogue", 12.5, 15.0)

        result = DialogueMatcher(threshold=99).best_match("expected words", [candidate])

        self.assertEqual(result.text, "unrelated dialogue")
        self.assertEqual(result.start_seconds, 12.5)
        self.assertLess(result.score, 99)

    def test_result_includes_a_caution_for_below_threshold_candidate(self):
        candidate = DialogueCandidate("unrelated dialogue", 12.5, 15.0, 45.0)

        result = ResultBuilder().build(
            candidate,
            frame_number=300,
            frame_image_url="/outputs/job/matched_frame.jpg",
            threshold=82,
            processing_time_seconds=3.456,
        )

        self.assertFalse(result.threshold_passed)
        self.assertIn("did not pass", result.caution or "")
        self.assertEqual(result.processing_time_seconds, 3.46)


if __name__ == "__main__":
    unittest.main()
