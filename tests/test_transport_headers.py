import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.video_ingest.format_policy import adaptive_stream_formats, format_attempts
from app.services.video_ingest.ytdlp_extractor import YtdlpMediaExtractor
from app.services.video_ingest.transport import apply_browser_headers, origin_headers


class TestOriginHeaders(unittest.TestCase):
    def test_okru_style_watch_url(self):
        headers = origin_headers("https://ok.ru/video/248244667877")
        self.assertEqual(headers["Referer"], "https://ok.ru/")
        self.assertEqual(headers["Origin"], "https://ok.ru")

    def test_impersonation_does_not_override_accept(self):
        options = apply_browser_headers({}, "https://ok.ru/video/1", impersonating=True)
        self.assertEqual(options["http_headers"]["Referer"], "https://ok.ru/")
        self.assertNotIn("User-Agent", options["http_headers"])

    def test_plain_tls_keeps_browser_ua(self):
        options = apply_browser_headers({}, "https://example.com/watch", impersonating=False)
        self.assertIn("Mozilla", options["http_headers"]["User-Agent"])

    def test_okru_prefers_adaptive_streams(self):
        self.assertTrue(YtdlpMediaExtractor._prefers_adaptive_stream("https://ok.ru/video/1"))
        self.assertEqual(format_attempts(720, prefer_adaptive=True)[0], adaptive_stream_formats(720))


if __name__ == "__main__":
    unittest.main()
