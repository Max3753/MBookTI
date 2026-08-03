from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.datetime_utils import UtcDatetime


class NotificationCreateRequest(BaseModel):
    """管理员定向消息。type: 2=管理员消息"""
    content: str = Field(min_length=1, max_length=500)


class NotificationResponse(BaseModel):
    id: int
    type: int          # 1=评论获赞 2=管理员消息
    content: str
    related_book_id: Optional[int] = None
    related_comment_id: Optional[int] = None
    is_read: bool
    created_at: UtcDatetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    unread: int = 0
