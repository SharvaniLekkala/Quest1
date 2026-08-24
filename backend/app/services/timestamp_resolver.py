from app.models.candidates import DialogueCandidate


class TimestampResolver:
    def resolve(self, candidate: DialogueCandidate) -> float:
        """Use the beginning of speech as the reproducible frame anchor."""
        return max(0.0, candidate.start_seconds)
