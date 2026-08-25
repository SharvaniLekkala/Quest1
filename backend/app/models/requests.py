from pydantic import AnyHttpUrl, BaseModel, Field


class DetectionRequest(BaseModel):
    video_url: AnyHttpUrl = Field(description="Publicly accessible video URL")
    target: str = Field(min_length=1, max_length=1_000, description="Dialogue to locate")
