# Video Dialogue Detector

Find the frame in a public video where a requested line of dialogue is spoken.
The project has a React/Vite web client and a local FastAPI service. The service
downloads a public video, reads captions when available, falls back to local
Faster-Whisper transcription, ranks dialogue candidates, and saves one JPEG
frame at the best match.

Only process videos you are permitted to download. The service supports public,
non-DRM watch URLs that `yt-dlp` can resolve; private, local, and reserved-network
URLs are rejected.

## Repository layout

```text
video-dialogue-detector/
├── backend/
│   ├── .env.example             # Safe configuration template
│   ├── requirements.txt         # Python runtime dependencies
│   └── app/
│       ├── api/routes.py        # HTTP endpoints and error conversion
│       ├── core/                # Settings and logging setup
│       ├── models/              # Request, response, candidate, and error models
│       ├── pipeline/            # Request validation and detection orchestration
│       ├── services/            # Downloading, transcription, matching, framing
│       │   └── video_ingest/    # yt-dlp format and HTTP transport policies
│       └── utils/               # Text, timestamp, and JSON helpers
├── frontend/
│   ├── src/                     # React UI and styles
│   ├── index.html               # Vite document entry point
│   ├── package.json             # Frontend scripts and dependencies
│   └── vite.config.js           # Vite configuration
├── tests/                       # Focused unit tests for active runtime behavior
├── run.py                       # Local backend launcher
└── README.md
```

Generated folders such as `outputs/`, Python virtual environments, Node modules,
and build output are intentionally excluded from version control and recreated as
needed.

## Architecture and design choices

### Why this architecture

The system separates HTTP handling, orchestration, domain models, and media
operations. This keeps the request path readable and lets a provider-specific
downloader, matching algorithm, or UI be replaced without changing the rest of
the application.

The application is deliberately synchronous and local. Downloading, caption
parsing, transcription, and frame extraction are CPU/network-heavy jobs, but a
synchronous design is easier to run and demonstrate for one video at a time.
For a multi-user deployment, place `DialogueDetector.detect` behind a job queue
and move generated outputs to object storage.

### Request-to-result map

```text
React form
  │ POST /api/v1/detect { video_url, target }
  ▼
api/routes.py → pipeline/detector.py
  │ validate → download → captions / Whisper → score → select frame → persist
  ▼
outputs/job_<id>/{source media, captions, matched_frame.jpg, result.json}
  │
  └── DetectionResult JSON → React result and image preview
```

### Backend module map

| Module | Used by | Responsibility and reason for the choice |
|---|---|---|
| `run.py` | Developer command | Starts Uvicorn in development-reload mode. It excludes `outputs/`, so generated media does not create noisy file-watch events or trigger reloads. |
| `app/main.py` | Uvicorn | Creates FastAPI, configures loopback-only CORS for Vite, mounts generated output files, and registers routes. |
| `app/api/routes.py` | FastAPI | Keeps endpoint definitions thin. It converts expected `PipelineError` failures into HTTP 422 responses. |
| `app/core/config.py` | App startup and detector | Loads typed settings from `backend/.env`; local paths are normalized once. |
| `app/core/logging_config.py` | `main.py` | Defines the timestamped console log format used by the `[progress]` messages. |
| `app/models/requests.py` | `/detect` | Defines and validates the public URL and target dialogue payload. |
| `app/models/responses.py` | Result builder and API | Defines the stable response contract, including score, threshold state, caution, and processing time. |
| `app/models/candidates.py` | Captions, Whisper, matcher | A small immutable transcript segment: text, start/end seconds, and score. |
| `app/models/errors.py` | Pipeline/services | Separates expected user-facing processing failures from unexpected server errors. |
| `app/pipeline/preprocessing.py` | Detector | Normalizes whitespace before matching while preserving the request model. |
| `app/pipeline/validation.py` | Detector | Rejects malformed and local/private URLs before a downloader can access them. |
| `app/pipeline/detector.py` | Route | The orchestration layer: creates a job directory, calls each service, chooses the best candidate, writes output, and measures elapsed time. |
| `app/services/video_downloader.py` | Detector | Job-level download facade. It discovers the downloaded media, obtains captions, and optionally retries via user-configured cookies/proxy. |
| `app/services/video_ingest/ytdlp_extractor.py` | Downloader | Encapsulates `yt-dlp` options, bounded retry logic, download progress reporting, and provider errors. |
| `app/services/video_ingest/format_policy.py` | Extractor | Keeps format strategies readable. It prefers adaptive HLS for OK.ru because its public CDN commonly rejects progressive variants. |
| `app/services/video_ingest/transport.py` | Extractor | Supplies browser-like headers, origin/referer, and optional TLS impersonation for hosts with anti-bot checks. |
| `app/services/subtitle_extractor.py` | Detector | Parses downloaded WebVTT captions first; captions are faster and generally more accurate than transcription. |
| `app/services/transcriber.py` | Detector | Uses Faster-Whisper only when captions are missing or weak, avoiding unnecessary model work. |
| `app/services/vad.py` | Detector | Removes empty/near-empty dialogue candidates before scoring. |
| `app/services/semantic_matcher.py` | Dialogue matcher | Combines normalized fuzzy similarity and word overlap. It is lightweight, deterministic, and has no remote embedding dependency. |
| `app/services/candidate_ranker.py` | Dialogue matcher | Selects highest score and then earliest occurrence for deterministic repeated-dialogue handling. |
| `app/services/dialogue_matcher.py` | Detector | Scores candidates and preserves the best below-threshold candidate instead of returning a fake first-frame result. |
| `app/services/timestamp_resolver.py` | Detector | Turns an imperfect subtitle/ASR span into a padded, phrase-focused seek window. |
| `app/services/frame_extractor.py` | Detector | Samples frames around speech, preferring temporal alignment, sharpness, and scene stability rather than blindly taking the first frame. |
| `app/services/result_builder.py` | Detector | Converts internal candidate data into the public response and creates a below-threshold caution. |
| `app/services/result_validator.py` | Detector | Verifies that a complete response and non-empty JPEG exist before success is returned. |
| `app/utils/text_utils.py` | Matching/timestamps | Applies a single consistent text-normalization rule. |
| `app/utils/time_utils.py` | Result builder | Formats seconds as a user-readable timestamp. |
| `app/utils/file_utils.py` | Detector | Writes `result.json` consistently. |

### Frontend module map

| File | Responsibility |
|---|---|
| `frontend/src/main.jsx` | React bootstrap and global stylesheet import. |
| `frontend/src/App.jsx` | Form state, API request, loading/error handling, caution display, and result rendering. |
| `frontend/src/styles.css` | Responsive, dependency-free visual styling for the page, forms, warning, and image. |
| `frontend/index.html` | Vite HTML shell and browser metadata. |
| `frontend/vite.config.js` | Vite/React development and build configuration. |
| `frontend/package.json` / `package-lock.json` | Reproducible frontend scripts and dependency versions. |

### Important implementation decisions

- **Captions before Whisper:** captions avoid model startup time and usually provide
  better time boundaries. Whisper is a fallback so the app still works when
  captions are unavailable or not a good match.
- **Best-match fallback, not a false failure:** a score below `MATCH_THRESHOLD`
  is still useful information. The API returns that best candidate with
  `threshold_passed: false` and a caution, rather than falsely reporting
  `"Failed to fetch"` and extracting frame zero.
- **Deterministic ranking:** the same input always gives the same answer; equal
  scores choose the earliest dialogue occurrence.
- **Frame window instead of an exact transcript timestamp:** subtitle and ASR
  timestamps drift. Sampling a short window and scoring frame quality reduces
  cut frames, blurry images, and frames dominated by subtitle text.
- **Generic public-video ingestion:** `yt-dlp` supports many sites, so the
  project avoids hard-coding a separate downloader per provider. Browser-like
  transport and bounded retries address common public-host failures without
  trying to bypass private or DRM-protected content.
- **Local-only defaults:** CORS accepts only `localhost`/`127.0.0.1`; outputs are
  served locally; cookie and proxy settings are opt-in and ignored by Git.

## Runtime flow

1. `POST /api/v1/detect` validates and normalizes the public URL and dialogue.
2. `VideoDownloader` resolves and downloads media and, when available, captions.
   OK.ru links prefer signed adaptive/HLS streams before progressive variants.
3. Caption segments are parsed and voice-filtered. If captions are absent or the
   caption match is below the configured threshold, Faster-Whisper transcribes
   the downloaded media.
4. `DialogueMatcher` scores candidates and selects the highest score; ties use
   the earliest occurrence.
5. `TimestampResolver` identifies a focused seeking window and `FrameExtractor`
   writes `matched_frame.jpg`.
6. The service validates the result, writes `result.json`, and returns the
   result to the client.

The backend logs `[progress]` messages for each stage plus throttled media
download progress. Completion includes elapsed server-side processing time.

## Requirements

- Python 3.10+ (Python 3.11 or 3.12 recommended)
- Node.js 20+ and npm
- Internet access for public-video downloads and the initial Whisper model fetch
- FFmpeg. `imageio-ffmpeg` supplies a bundled executable, but a system FFmpeg
  installation on `PATH` is recommended.

## Setup

From the repository root:

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
Copy-Item .env.example .env
cd ..
```

If PowerShell blocks activation, run the following once in that shell:

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

Create `backend/.env` from `.env.example`. It is local-only and must not be
committed.

```ini
# Runtime artifacts. Relative paths are resolved from backend/.
OUTPUT_DIR=outputs

# Faster-Whisper model: tiny, base, small, medium, or large-v3.
WHISPER_MODEL=small

# Minimum match score (0–100) considered a passing match.
MATCH_THRESHOLD=82

# Maximum source-video height. Lower values reduce download size and processing time.
MAX_VIDEO_HEIGHT=720

# Optional Netscape cookie file for sites that require an authenticated session.
# COOKIES_FILE=C:\secure\provider-cookies.txt

# Or read cookies from a closed local browser, for example chrome.
# COOKIES_FROM_BROWSER=chrome

# Optional HTTP/SOCKS proxy. Leave empty for the direct connection.
# DOWNLOAD_PROXY=
```

Do not share cookie files or route authenticated cookies through an untrusted
proxy.

## Run locally

Use two terminals.

Backend:

```powershell
cd C:\Users\Sharvani\Desktop\Quest1\video-dialogue-detector
.\backend\.venv\Scripts\Activate.ps1
python run.py
```

The API listens on `http://127.0.0.1:8000`; interactive OpenAPI documentation
is at `http://127.0.0.1:8000/docs`.

Frontend:

```powershell
cd C:\Users\Sharvani\Desktop\Quest1\video-dialogue-detector\frontend
npm run dev
```

Open the Vite address printed in the terminal, normally
`http://127.0.0.1:5173`.

To point the frontend at a different API, create `frontend/.env.local`:

```ini
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

## API

### Health check

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

### Detect a dialogue frame

```powershell
$body = @{
  video_url = "https://example.com/public-video"
  target = "the dialogue to locate"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/detect `
  -ContentType "application/json" `
  -Body $body
```

Successful requests return HTTP `201` with one best result:

```json
{
  "timestamp": "00:01:23.456",
  "frame_number": 2504,
  "extracted_text": "The closest dialogue segment.",
  "frame_image": "/outputs/job_<id>/matched_frame.jpg",
  "score": 73.2,
  "confidence": "medium",
  "threshold_passed": false,
  "caution": "Best available match did not pass the configured 82% threshold and may not be accurate.",
  "processing_time_seconds": 42.31
}
```

A below-threshold candidate remains a valid response: the service returns the
best available match and the UI shows the caution beneath the result heading.
It never substitutes a fake first-frame result. A genuine inability to download,
transcribe, or extract spoken dialogue returns HTTP `422` with a descriptive
`detail` message.

## Tests and verification

Run the focused tests after activating the backend environment:

```powershell
$env:PYTHONPATH = "$PWD\backend"
python -m unittest discover -s tests -p "test_*.py" -v
```

Build the frontend production bundle:

```powershell
cd frontend
npm run build
```

## Operational notes

- First transcription can take longer because Faster-Whisper may download and
  initialize a model.
- Public video providers can rate-limit, region-block, or reject automation.
  The downloader uses browser-like headers/TLS profiles where available and
  retries bounded transient failures; it cannot bypass private access or DRM.
- Each request creates an `outputs/job_<id>/` directory containing source media,
  captions, the extracted image, and `result.json`. Treat it as disposable
  runtime data and clean it according to your storage policy.
