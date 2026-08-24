from pathlib import Path


def output_stem(video_path: Path) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in video_path.stem)
