from app.models.candidates import DialogueCandidate


class VoiceActivityFilter:
    """Drops empty transcription segments; Whisper performs the actual VAD."""

    def filter(self, candidates: list[DialogueCandidate]) -> list[DialogueCandidate]:
        return [candidate for candidate in candidates if candidate.text.strip() and candidate.end_seconds > candidate.start_seconds]
