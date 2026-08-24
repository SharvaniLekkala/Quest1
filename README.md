# Video Dialogue Detector

Find the frame in a public video where a requested line of dialogue occurs. The project includes a React interface and a modular FastAPI backend.

Input:

```json
{
  "video_url": "https://public-video.example/watch?id=123",
  "target": "the dialogue text to find"
}
```

Output: exactly one result, returned by the API and saved as JSON.

```json
{
  "timestamp": "00:01:23.456",
  "frame_number": 2504,
  "extracted_text": "The dialogue spoken at this point.",
  "frame_image": "/outputs/job_<id>/matched_frame.jpg"
}
```

## Features implemented

- React form for a public video URL and dialogue text.
- Result UI that prints the timestamp, frame number, extracted text, and matched image.
- Single public-video downloads through `yt-dlp`; playlists are disabled.
- Subtitle and automatic-caption parsing first for efficient long-video processing.
- Local Faster-Whisper transcription fallback when subtitles are unavailable.
- Voice-activity filtering, language-detection, audio-processing, diarization, and cache extension points.
- Lexical/semantic-style dialogue scoring with a configurable confidence threshold.
- Deterministic ambiguity handling: the highest-scoring match wins; ties use the earliest occurrence.
- Timestamp-based OpenCV frame extraction.
- One job folder per request containing source media, the JPEG frame, and `result.json`.
- Input/output validation, readable API errors, local URL/private-IP rejection, CORS, and static image serving.
- Git protection for local configuration, secrets, credentials, dependencies, caches, and generated artifacts.

## Project structure

```text
video-dialogue-detector/
├── backend/
│   ├── .env.example              # Safe configuration template
│   ├── requirements.txt
│   └── app/
│       ├── api/                  # FastAPI routes
│       ├── core/                 # Configuration and logging
│       ├── models/               # Request, response, error, candidate models
│       ├── pipeline/             # Validation, preprocessing, orchestration helpers
│       ├── services/             # Download, subtitles, transcription, matching, frames
│       └── utils/                # Time, text, file, audio helpers
├── frontend/
│   ├── src/App.jsx               # React form and result view
│   ├── src/styles.css            # Basic responsive styling
│   ├── package.json
│   └── vite.config.js
├── outputs/                      # Created at runtime; ignored by Git
├── run.py                        # Starts the backend API
└── README.md
```

## Prerequisites

- Python 3.10+ (3.11 or 3.12 recommended).
- Node.js 20+ and npm for the React/Vite frontend.
- [FFmpeg](https://ffmpeg.org/download.html) available on `PATH` for media handling and Whisper.
- Internet access for public-video downloads and the first Whisper model download.

Only submit videos you are permitted to download and process. URLs must be public, supported by `yt-dlp`, and not DRM-protected. Private, access-controlled, local, or reserved-network URLs are rejected or will fail to download.

## Install

Open PowerShell in the project root:

```powershell
cd C:\Users\Sharvani\Desktop\Quest1\video-dialogue-detector
```

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env -Force
cd ..
```

If PowerShell prevents activation, run this once in that shell and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Frontend

```powershell
cd frontend
npm install
cd ..
```

## Configuration

Set optional values in `backend/.env`. Do not commit it.

```ini
# Directory for generated job artifacts. Default: <project>/outputs
OUTPUT_DIR=outputs

# Used only when subtitles cannot be used: base, small, medium, large-v3
WHISPER_MODEL=small

# Minimum score from 0 to 100. Higher values require closer text.
MATCH_THRESHOLD=82

# Download resolution limit. Lower values reduce disk and processing time.
MAX_VIDEO_HEIGHT=720
```

The frontend defaults to `http://127.0.0.1:8000/api/v1`. To use another API, create ignored file `frontend/.env.local`:

```ini
VITE_API_URL=https://your-api.example/api/v1
```

## Run the project

Use two PowerShell windows.

### Terminal 1 — backend API

```powershell
cd C:\Users\Sharvani\Desktop\Quest1\video-dialogue-detector
.\backend\.venv\Scripts\Activate.ps1
python run.py
```

The API runs at `http://127.0.0.1:8000`.

### Terminal 2 — React frontend

```powershell
cd C:\Users\Sharvani\Desktop\Quest1\video-dialogue-detector\frontend
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Paste a public video URL, enter a line of dialogue, and select **Find frame**.

## Verify it is working

### API health check

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{"status":"ok"}
```

### Send a request directly

```powershell
$body = @{
  video_url = "<public-video-url>"
  target = "<dialogue text>"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/detect `
  -ContentType "application/json" `
  -Body $body
```

Success returns HTTP `201` and the four-field result. Open `http://127.0.0.1:8000` plus the returned `frame_image` value to inspect the JPEG. Its job folder also contains the persisted `result.json`.

### Build the frontend

```powershell
cd frontend
npm run build
```

This creates `frontend/dist/`, which is intentionally ignored by Git.

## API reference

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/v1/health` | `GET` | Lightweight readiness check. |
| `/api/v1/detect` | `POST` | Download, locate dialogue, extract a frame, and save JSON. |
| `/docs` | `GET` | Interactive FastAPI/OpenAPI documentation. |
| `/outputs/...` | `GET` | Generated local artifacts, including matched images. |

`POST /api/v1/detect` expects:

```json
{
  "video_url": "https://example.org/public-video",
  "target": "the exact or near-exact dialogue to find"
}
```

If processing cannot complete, `/detect` returns HTTP `422` with a descriptive `detail`. Typical causes: unsupported/private URL, unavailable captions plus failed transcription, no speech, low-confidence text match, or unreadable video frame.

## Processing flow

1. Validate and normalize the request.
2. Download the source video and available captions.
3. Parse captions, or transcribe locally with Faster-Whisper when necessary.
4. Filter empty speech segments and score candidates against the target dialogue.
5. Select one candidate: highest score, then earliest timestamp for ties.
6. Seek to that timestamp, save the JPEG, validate it, and write `result.json`.

For variable-frame-rate media, timestamp seeking is the reliable reference. The JPEG and timestamp are authoritative; encoded frame numbers can vary slightly by decoder.

## Security and Git hygiene

`.gitignore` excludes `.env` files, credential folders, private keys/certificates, virtual environments, Python caches, npm dependencies, npm cache, built frontend files, and generated video outputs. Keep API tokens, private URLs, and other sensitive data only in ignored local configuration files.

## Current scope

This is a synchronous, local single-video implementation. Production deployment should add authentication, rate limits, queue workers, object storage, a database, output-retention cleanup, strict DNS-aware domain allow-listing, and a dedicated embedding model for robust paraphrase matching.
