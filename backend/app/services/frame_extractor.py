from pathlib import Path

import cv2

from app.models.errors import PipelineError


class FrameExtractor:
    def extract(self, video_path: Path, timestamp_seconds: float, output_path: Path) -> int:
        capture = cv2.VideoCapture(str(video_path))
        try:
            if not capture.isOpened():
                raise PipelineError("OpenCV could not open the downloaded video.")
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000)
            success, frame = capture.read()
            if not success:
                raise PipelineError("Could not decode a frame at the matched timestamp.")
            frame_number = int(capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(output_path), frame):
                raise PipelineError("Could not write the extracted image.")
            return frame_number
        finally:
            capture.release()
