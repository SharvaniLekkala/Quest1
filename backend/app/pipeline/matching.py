from app.models.candidates import DialogueCandidate
from app.services.candidate_ranker import CandidateRanker
from app.services.semantic_matcher import SemanticMatcher


class MatchingPipeline:
    """Ranks possible occurrences deterministically when dialogue is repeated."""

    def __init__(self) -> None:
        self.semantic_matcher = SemanticMatcher()
        self.ranker = CandidateRanker()

    def select(self, target: str, candidates: list[DialogueCandidate]) -> DialogueCandidate:
        scored = [self.semantic_matcher.score(target, candidate) for candidate in candidates]
        return self.ranker.select_one(scored)
