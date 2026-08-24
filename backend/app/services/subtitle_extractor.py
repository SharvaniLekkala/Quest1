import re
from pathlib import Path

from app.models.candidates import DialogueCandidate


class SubtitleExtractor:
    """Parses WebVTT subtitles saved alongside a downloaded video."""

    def extract(self, directory: Path) -> list[DialogueCandidate]:
        candidates: list[DialogueCandidate] = []
        for subtitle in directory.glob("*.vtt"):
            content = subtitle.read_text(encoding="utf-8", errors="replace")
            blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n"))
            for block in blocks:
                lines = [line.strip() for line in block.splitlines() if line.strip()]
                timing = next((line for line in lines if " --> " in line), None)
                if not timing:
                    continue
                text = " ".join(line for line in lines if line != timing and not line.isdigit() and not line.startswith("WEBVTT"))
                text = re.sub(r"<[^>]+>", "", text)
                if text:
                    start, end = timing.split(" --> ", 1)
                    candidates.append(DialogueCandidate(text, self._seconds(start), self._seconds(end.split()[0])))
        return candidates

    @staticmethod
    def _seconds(value: str) -> float:
        parts = value.replace(",", ".").split(":")
        return sum(float(part) * 60 ** position for position, part in enumerate(reversed(parts)))
