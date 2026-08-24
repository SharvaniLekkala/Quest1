from app.models.candidates import DialogueCandidate
from app.models.errors import PipelineError


class CandidateRanker:
    """Stable ranking policy: confidence first, then earliest occurrence."""

    def select_one(self, candidates: list[DialogueCandidate]) -> DialogueCandidate:
        if not candidates:
            raise PipelineError("No dialogue candidates are available to rank.")
        # Repeated dialogue can be genuinely ambiguous. Choosing the earliest
        # occurrence makes the API deterministic while retaining a single result.
        return sorted(candidates, key=lambda item: (-item.score, item.start_seconds, item.end_seconds))[0]
