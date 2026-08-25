from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings
from app.core.logging_config import configure_logging

configure_logging()
app = FastAPI(title="Video Dialogue Detector", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    # Vite may select the next free local port when 5173 is occupied. Accept
    # only loopback browser origins, on any development port, so preflight
    # requests stay local without coupling the API to one Vite port.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(router)
settings.output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=settings.output_dir), name="outputs")


@app.get("/", tags=["service"])
def root() -> dict[str, str]:
    """Provide a useful response when the API URL is opened in a browser."""
    return {
        "message": "Video Dialogue Detector API is running.",
        "docs": "/docs",
        "health": "/api/v1/health",
        "frontend": "http://127.0.0.1:5173",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Avoid a noisy 404 for browsers that automatically request a favicon."""
    return Response(status_code=204)
