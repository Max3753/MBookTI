from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.datetime_utils import UtcDatetime

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None
    cover_url: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    language: str = "zh"
    created_at: UtcDatetime
    
    model_config = {"from_attributes": True}


class RecommendedTypeInfo(BaseModel):
    code: str
    name: str


class BookRatingRequest(BaseModel):
    """书籍评分请求（1-5 星）"""
    rating: int = Field(ge=1, le=5)


class BookRatingResponse(BaseModel):
    """书籍评分响应（DELETE 取消评分时 rating 为 None）"""
    rating: Optional[int] = None


class BookDetailResponse(BaseModel):
    id: int
    title: str
    author: str
    cover_url: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    recommended_types: list[RecommendedTypeInfo] = []
    comment_count: int = 0
    is_favorited: bool = False
    # 评分汇总：avg_rating 无评分时为 None；my_rating 未登录或未评分为 None
    avg_rating: Optional[float] = None
    rating_count: int = 0
    my_rating: Optional[int] = None
    created_at: UtcDatetime

    model_config = {"from_attributes": True}
