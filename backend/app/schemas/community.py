# 社区动态（Feed）数据模型
from typing import Optional
from pydantic import BaseModel
from app.schemas.datetime_utils import UtcDatetime


class FeedItem(BaseModel):
    """社区动态条目：书评(comment) / 收藏(favorite) 两种类型。

    comment 类型携带 comment_id/content/parent_id；
    favorite 类型这三个字段为 None。
    """
    type: str  # 'comment' | 'favorite'
    id: int
    user_id: int
    username: str
    avatar_url: Optional[str] = None
    created_at: UtcDatetime
    book_id: int
    book_title: str
    book_cover_url: Optional[str] = None
    comment_id: Optional[int] = None
    content: Optional[str] = None
    parent_id: Optional[int] = None
