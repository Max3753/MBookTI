from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.datetime_utils import UtcDatetime


class CommentCreateRequest(BaseModel):
    book_id: int
    content: str = Field(min_length=1, max_length=2000)
    parent_id: Optional[int] = None


class CommentResponse(BaseModel):
    id: int
    user_id: int
    username: str
    avatar_url: Optional[str] = None
    book_id: int
    parent_id: Optional[int] = None
    content: str
    likes_count: int
    is_edited: bool
    created_at: UtcDatetime

    model_config = {"from_attributes": True}


class MyCommentResponse(BaseModel):
    """我的书评（含书籍信息）"""
    id: int
    book_id: int
    book_title: str
    book_cover_url: Optional[str] = None
    parent_id: Optional[int] = None
    content: str
    likes_count: int
    created_at: UtcDatetime
