from app.models.candidates import DialogueCandidate
from app.models.errors import PipelineError
from app.services.candidate_ranker import CandidateRanker
from app.services.semantic_matcher import SemanticMatcher


class DialogueMatcher:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold
        self.semantic_matcher = SemanticMatcher()
        self.ranker = CandidateRanker()

    def best_match(self, target: str, candidates: list[DialogueCandidate]) -> DialogueCandidate:
        if not candidates:
            raise PipelineError("No speech or subtitles were found in the video.")
        best = self.ranker.select_one([self.semantic_matcher.score(target, candidate) for candidate in candidates])
        if best.score < self.threshold:
            raise PipelineError(f"No sufficiently close dialogue match was found (best score: {best.score:.1f}).")
        return best
