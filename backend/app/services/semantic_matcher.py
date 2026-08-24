from rapidfuzz.fuzz import ratio

from app.models.candidates import DialogueCandidate
from app.utils.text_utils import normalize_text


class SemanticMatcher:
    """Lightweight lexical-semantic score without a remote model dependency."""

    def score(self, target: str, candidate: DialogueCandidate) -> DialogueCandidate:
        expected, actual = normalize_text(target), normalize_text(candidate.text)
        if expected in actual:
            score = 100.0
        else:
            expected_terms, actual_terms = set(expected.split()), set(actual.split())
            overlap = len(expected_terms & actual_terms) / len(expected_terms | actual_terms) if expected_terms or actual_terms else 0.0
            score = max(float(ratio(expected, actual)), overlap * 100)
        return DialogueCandidate(candidate.text, candidate.start_seconds, candidate.end_seconds, score)
