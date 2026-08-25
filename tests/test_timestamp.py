import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.timestamp_resolver import TimestampResolver
from app.models.candidates import DialogueCandidate


class TestTimestampResolver(unittest.TestCase):
    def test_resolve(self):
        resolver = TimestampResolver()
        candidate = DialogueCandidate(text="hello", start_seconds=5.5, end_seconds=6.5)
        self.assertEqual(resolver.resolve(candidate), 5.5)

        candidate_negative = DialogueCandidate(text="hello", start_seconds=-1.0, end_seconds=2.0)
        self.assertEqual(resolver.resolve(candidate_negative), 0.0)

    def test_window_pads_asr_error(self):
        resolver = TimestampResolver()
        candidate = DialogueCandidate(text="the line", start_seconds=8.0, end_seconds=9.0)
        window = resolver.resolve_window(candidate, "the line")
        self.assertLess(window.search_start, 8.0)
        self.assertGreater(window.search_end, 9.0)
        self.assertGreater(window.anchor, 8.0)


if __name__ == "__main__":
    unittest.main()
