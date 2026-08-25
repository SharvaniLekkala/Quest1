# Video Dialogue Detector

**Project Overview**

This repository implements a tool that locates a specific line of dialogue within a publicly‑available video and extracts the exact frame where it occurs. It combines a React front‑end for user interaction with a FastAPI back‑end that downloads videos via `yt-dlp`, processes subtitles or runs Whisper transcription, matches the target phrase, and returns the timestamp, frame number, extracted text, and a JPEG image.

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
- Generic public-video ingestion through `yt-dlp` (browser-like TLS via `curl_cffi` when hosts fingerprint handshakes); playlists are disabled. Any publicly accessible watch URL the extractor can resolve is accepted, not only YouTube.
- English subtitle and automatic-caption parsing first for efficient long-video processing; other languages fall back to local transcription.
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
- FFmpeg support is required for the common separate video/audio streams provided by YouTube and many other platforms. `imageio-ffmpeg` installs a bundled executable with the backend requirements; a system [FFmpeg](https://ffmpeg.org/download.html) installation on `PATH` is also supported and preferred for widest compatibility.
- Internet access for public-video downloads and the first Whisper model download. Backend requirements include `curl_cffi` so the downloader can impersonate a browser TLS fingerprint on hosts that drop Python's default SSL handshake.

Only submit videos you are permitted to download and process. URLs must be public, resolvable by the generic extractor (`yt-dlp`), and not DRM-protected. Private, access-controlled, local, or reserved-network URLs are rejected or will fail to download.

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

# Whisper model used when subtitles are unavailable.
# Options: tiny (fastest), base, small, medium, large-v3 (most accurate).
# Default: tiny — good balance of speed and accuracy for short clips.
WHISPER_MODEL=tiny

# Minimum score from 0 to 100. Higher values require closer text.
# When the best candidate scores below this threshold the API still returns
# the result but marks its confidence as "medium" or "low".  Default: 70.
MATCH_THRESHOLD=70

# Download resolution limit. Lower values reduce disk and processing time.
MAX_VIDEO_HEIGHT=720

# Enable lightweight noise reduction on extracted audio before transcription.
# Uses the noisereduce library (~0.2 s per minute of audio).  Default: true.
ENABLE_NOISE_REDUCTION=true
```

### Score and confidence

The API response now includes two extra fields:

```json
{
  "timestamp": "00:01:23.456",
  "frame_number": 2504,
  "extracted_text": "The dialogue spoken at this point.",
  "frame_image": "/outputs/job_<id>/matched_frame.jpg",
  "score": 73.2,
  "confidence": "medium"
}
```

| Score range | Confidence label |
|-------------|-----------------|
| 80 – 100    | `high`          |
| 60 – 79     | `medium`        |
| 0 – 59      | `low`           |

Even when the score is below the threshold the API returns the best match
instead of failing with HTTP 422. The client can use `confidence` to decide
how to present the result (e.g. show a warning badge for "medium" or "low").

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

The API runs at `http://127.0.0.1:8000`. Opening it directly shows service links; use `/docs` for API documentation. The React user interface runs separately on port `5173`.

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

If processing cannot complete, `/detect` returns HTTP `422` with a descriptive `detail`. Typical causes: unsupported/private URL, provider rate-limiting that also blocks video download, unavailable captions plus failed transcription, no speech, low-confidence text match, or unreadable video frame. A subtitle-only rate limit falls back to local Whisper transcription.

Some providers may temporarily reject automated requests, returning errors such as HTTP `429`, Windows `10054` (connection forcibly closed), or curl error `35` / `SSL_ERROR_SYSCALL`. The downloader retries bounded transient failures using current Chrome, Firefox, and Edge TLS profiles where supported, and uses yt-dlp's native HLS downloader for signed HLS streams so fragments keep the same request context. A TLS reset occurs before HTTP is established: it is not a certificate error, so `nocheckcertificate` and repeated retries cannot bypass it. Confirm that the exact public URL opens in a normal browser on the same machine and network, remove any untrusted `DOWNLOAD_PROXY`, and retry later or from a network where the public page is available.

For a provider that opens in your own browser only after sign-in, you may export a Netscape-format cookies file and set its local, ignored path with `COOKIES_FILE=C:\secure\provider-cookies.txt` in `backend/.env`. Never commit or share this file: it grants access to your signed-in browser session. This option cannot override a provider or network that closes all connections before authentication.

As an alternative to exporting a file, set `COOKIES_FROM_BROWSER=chrome` (or another yt-dlp-supported browser) in `backend/.env` after fully closing that browser. This is a generic transport option for sites whose public media stream still requires the session cookies created by a normal browser. Do not set both cookie options unless you intentionally want the file to take precedence.

If a network requires it, `DOWNLOAD_PROXY` accepts an HTTP or SOCKS proxy URL and is applied uniformly to public-video requests. Leave it unset for the normal network connection. Do not send browser cookies through a proxy you do not trust.

## Processing flow

1. Validate and normalize the request.
2. Download the source video and available captions.
3. Parse captions, or extract mono 16 kHz audio and optionally apply noise reduction, then transcribe locally with Faster-Whisper.
4. Filter empty speech segments and score candidates against the target dialogue.
5. Select one candidate: highest score, then earliest timestamp for ties. If the score is below the threshold, return it anyway with a `"medium"` or `"low"` confidence label.
6. Seek to that timestamp, save the JPEG, validate it, and write `result.json`.

For variable-frame-rate media, timestamp seeking is the reliable reference. The JPEG and timestamp are authoritative; encoded frame numbers can vary slightly by decoder.

## Security and Git hygiene

`.gitignore` excludes `.env` files, credential folders, private keys/certificates, virtual environments, Python caches, npm dependencies, npm cache, built frontend files, and generated video outputs. Keep API tokens, private URLs, and other sensitive data only in ignored local configuration files.

## Troubleshooting

- **`[SSL: UNEXPECTED_EOF_WHILE_READING]`** — the host dropped the TLS handshake (common TLS fingerprinting). Confirm `curl_cffi` is installed so yt-dlp can impersonate a browser. Do not bind `source_address` on Windows; that combination can crash curl_cffi.
- **HTTP 403 on a media URL** — the page may have resolved, but that stream is blocked. The extractor retries adaptive (HLS/DASH) formats automatically. Session cookies (`COOKIES_FILE`) still help when a “public” page actually requires a logged-in view.
- **Connection reset / `WinError 10054`** — transient anti-bot or rate limiting; the downloader retries with backoff. Switch networks or retry later if it persists.

## Current scope

This is a synchronous, local single-video implementation. Production deployment should add authentication, rate limits, queue workers, object storage, a database, output-retention cleanup, strict DNS-aware domain allow-listing, and a dedicated embedding model for robust paraphrase matching.
