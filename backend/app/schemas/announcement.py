from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=5000)


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    content: str
    is_active: bool
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}
