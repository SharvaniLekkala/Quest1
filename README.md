# Video Dialogue Detector

A modular FastAPI backend that accepts a public video URL and a dialogue target, then produces one matched result:

```json
{
  "timestamp": "00:01:23.456",
  "frame_number": 2504,
  "extracted_text": "The dialogue spoken at this point.",
  "frame_image": "C:\\...\\outputs\\job_<id>\\matched_frame.jpg"
}
```

The result is also saved to `outputs/job_<id>/result.json`, alongside the downloaded source and frame image.

## What is implemented

- Public-video downloading through `yt-dlp` (one video only; no playlists).
- Subtitle/automatic-caption parsing first, which makes long videos efficient where captions are available.
- Local `faster-whisper` speech transcription fallback with voice-activity detection.
- Fuzzy dialogue matching with an adjustable confidence threshold.
- Timestamp-based frame extraction through OpenCV and JSON result persistence.
- A small, versioned REST API with validation and human-readable error responses.

The backend is arranged by responsibility: `services/` contains integrations and focused operations, `pipeline/detector.py` orchestrates them, `models/` owns API data contracts, and `utils/` contains side-effect-free helpers. This keeps providers and matching strategies easy to swap later.

## Prerequisites

- Python 3.10+ (3.11 or 3.12 recommended)
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on `PATH` (required for reliable media processing and Whisper)
- Internet access for public-video downloads and the first Whisper model download

Use only videos you are allowed to download and process. A URL must be public and supported by `yt-dlp`; access-controlled, DRM-protected, or private videos will fail.

## Install

From the project root in PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Optional settings in `backend/.env`:

```ini
OUTPUT_DIR=outputs
WHISPER_MODEL=small
MATCH_THRESHOLD=82
MAX_VIDEO_HEIGHT=720
```

For a faster, lower-accuracy fallback transcription use `WHISPER_MODEL=base`; `small` is the default balance. Subtitle matching does not load Whisper.

## Run and check it

Start the API from the project root:

```powershell
python run.py
```

Confirm the server is running:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{"status":"ok"}
```

Submit a detection request (replace both placeholders):

```powershell
$body = @{ video_url = "<public-video-url>"; target = "<dialogue text>" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/detect -ContentType "application/json" -Body $body
```

The response is the required single result. Open the returned `frame_image` path and its sibling `result.json` to verify that the time, frame, text, and JPEG agree. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## API contract

`POST /api/v1/detect`

```json
{
  "video_url": "https://example.org/public-video",
  "target": "the exact or near-exact dialogue to find"
}
```

A successful request returns HTTP `201`. If downloading, transcription, or matching cannot complete, the API returns `422` with a descriptive `detail` message. `GET /api/v1/health` returns HTTP `200` without contacting external services.

## Current scope and next increments

The initial backend is complete for synchronous single-video jobs. For production-scale long-video traffic, add a persistent job queue (Celery/RQ), object storage for artifacts, a database for job metadata, URL/domain allow-listing, cleanup retention, auth/rate limits, and a semantic embedding matcher for paraphrased targets. Variable-frame-rate sources are timestamp-seeked correctly, but an encoded "frame number" is inherently decoder-dependent; the JPEG and timestamp are the authoritative match artifacts.
