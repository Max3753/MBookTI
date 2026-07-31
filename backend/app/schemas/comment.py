from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CommentCreateRequest(BaseModel):
    recommendation_id: int
    content: str
    parent_id: Optional[int] = None


class CommentResponse(BaseModel):
    id: int
    user_id: int
    username: str
    recommendation_id: int
    parent_id: Optional[int] = None
    content: str
    likes_count: int
    is_edited: bool
    created_at: datetime

    model_config = {"from_attributes": True}
