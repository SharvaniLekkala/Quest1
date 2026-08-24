from fastapi import FastAPI

from app.api.routes import router
from app.core.logging_config import configure_logging

configure_logging()
app = FastAPI(title="Video Dialogue Detector", version="1.0.0")
app.include_router(router)
