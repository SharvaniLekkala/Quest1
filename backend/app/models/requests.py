from pydantic import AnyHttpUrl, BaseModel, Field


class DetectionRequest(BaseModel):
    video_url: AnyHttpUrl = Field(description="Public URL supported by yt-dlp")
    target: str = Field(min_length=1, max_length=1_000, description="Dialogue to locate")
