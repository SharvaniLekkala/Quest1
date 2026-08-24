from pathlib import Path


def wav_path_for(video_path: Path) -> Path:
    return video_path.with_suffix(".wav")
