from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.datetime_utils import UtcDatetime


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=5000)


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    content: str
    is_active: bool
    created_by: int
    created_at: UtcDatetime

    model_config = {"from_attributes": True}
