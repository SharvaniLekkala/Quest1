from dataclasses import dataclass

from app.models.candidates import DialogueCandidate
from app.utils.text_utils import normalize_text


@dataclass(frozen=True)
class FrameSearchWindow:
    """Speech-centered window used for frame sampling.

    ``anchor`` is the best estimate of when the target line is actually spoken.
    ``search_start`` / ``search_end`` pad that instant for ASR/subtitle jitter
    without treating the Whisper timestamp as exact.
    """

    search_start: float
    search_end: float
    anchor: float


class TimestampResolver:
    """Maps a matched transcript span onto a robust frame-search window."""

    # Typical subtitle/Whisper endpoint error on music, noise, and fast edits.
    _ASR_PAD_BEFORE = 0.35
    _ASR_PAD_AFTER = 0.45
    _MIN_WINDOW = 0.8
    _MAX_WINDOW = 2.4

    def resolve(self, candidate: DialogueCandidate) -> float:
        """Use the beginning of speech as the reproducible frame anchor."""
        return max(0.0, candidate.start_seconds)

    def resolve_window(self, candidate: DialogueCandidate, target: str = "") -> FrameSearchWindow:
        start, end = self._phrase_span(candidate, target)
        duration = max(0.0, end - start)
        # Sit a short way into the utterance so a cut exactly at start_seconds
        # is not treated as the dialogue frame.
        into_speech = min(0.28, 0.32 * duration) if duration > 0 else 0.0
        anchor = max(0.0, start + into_speech)

        search_start = max(0.0, start - self._ASR_PAD_BEFORE)
        search_end = end + self._ASR_PAD_AFTER
        width = search_end - search_start
        if width < self._MIN_WINDOW:
            extra = (self._MIN_WINDOW - width) / 2.0
            search_start = max(0.0, search_start - extra)
            search_end = search_end + extra
        elif width > self._MAX_WINDOW:
            search_start = max(search_start, anchor - self._MAX_WINDOW / 2.0)
            search_end = min(search_end, anchor + self._MAX_WINDOW / 2.0)
            if search_end - search_start < self._MIN_WINDOW:
                search_end = search_start + self._MIN_WINDOW

        return FrameSearchWindow(search_start=search_start, search_end=search_end, anchor=anchor)

    def _phrase_span(self, candidate: DialogueCandidate, target: str) -> tuple[float, float]:
        start = max(0.0, candidate.start_seconds)
        end = max(start, candidate.end_seconds)
        if end <= start:
            end = start + 0.5

        expected = normalize_text(target).split()
        actual = normalize_text(candidate.text).split()
        if not expected or not actual or len(actual) == 1:
            return start, end

        index = _subsequence_index(actual, expected)
        if index is None:
            return start, end

        n = len(actual)
        duration = end - start
        phrase_start = start + duration * (index / n)
        phrase_end = start + duration * ((index + len(expected)) / n)
        if phrase_end <= phrase_start:
            phrase_end = phrase_start + duration / max(n, 1)
        return phrase_start, phrase_end


def _subsequence_index(haystack: list[str], needle: list[str]) -> int | None:
    n, m = len(haystack), len(needle)
    if m > n:
        return None
    for i in range(n - m + 1):
        if haystack[i : i + m] == needle:
            return i
    return None
