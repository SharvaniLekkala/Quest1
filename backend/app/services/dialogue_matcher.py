import logging

from app.models.candidates import DialogueCandidate
from app.models.errors import PipelineError
from app.services.candidate_ranker import CandidateRanker
from app.services.semantic_matcher import SemanticMatcher

logger = logging.getLogger(__name__)


class DialogueMatcher:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold
        self.semantic_matcher = SemanticMatcher()
        self.ranker = CandidateRanker()

    def best_match(self, target: str, candidates: list[DialogueCandidate]) -> DialogueCandidate:
        if not candidates:
            raise PipelineError("No spoken dialogue could be extracted from this video.")
            
        best = self.ranker.select_one([self.semantic_matcher.score(target, candidate) for candidate in candidates])
        
        if best.score < self.threshold:
            logger.warning(
                "Best dialogue match score %.1f is below threshold %.1f — "
                "returning fallback result",
                best.score,
                self.threshold,
            )
        return best
