from rapidfuzz.fuzz import ratio

from app.models.candidates import DialogueCandidate
from app.models.errors import PipelineError
from app.utils.text_utils import normalize_text


class DialogueMatcher:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def best_match(self, target: str, candidates: list[DialogueCandidate]) -> DialogueCandidate:
        normalized_target = normalize_text(target)
        scored = []
        for candidate in candidates:
            normalized_candidate = normalize_text(candidate.text)
            score = 100.0 if normalized_target in normalized_candidate else ratio(normalized_target, normalized_candidate)
            scored.append(DialogueCandidate(candidate.text, candidate.start_seconds, candidate.end_seconds, score))
        if not scored:
            raise PipelineError("No speech or subtitles were found in the video.")
        best = max(scored, key=lambda item: item.score)
        if best.score < self.threshold:
            raise PipelineError(f"No sufficiently close dialogue match was found (best score: {best.score:.1f}).")
        return best
