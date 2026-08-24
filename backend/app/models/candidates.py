from dataclasses import dataclass


@dataclass(frozen=True)
class DialogueCandidate:
    text: str
    start_seconds: float
    end_seconds: float
    score: float = 0.0
