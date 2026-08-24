from app.models.candidates import DialogueCandidate


class SpeakerDiarizer:
    """No-op default; replace with a diarization provider when speaker labels are required."""

    def annotate(self, candidates: list[DialogueCandidate]) -> list[DialogueCandidate]:
        return candidates
