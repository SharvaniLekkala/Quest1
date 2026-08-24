import re


class LanguageDetector:
    """Reports a conservative script classification without an extra model dependency."""

    def detect(self, text: str) -> str:
        if re.search(r"[\u0900-\u097F]", text):
            return "hi"
        if re.search(r"[A-Za-z]", text):
            return "en"
        return "und"
