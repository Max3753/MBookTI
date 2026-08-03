from typing import Optional
from pydantic import BaseModel
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
    created_at: UtcDatetime

    model_config = {"from_attributes": True}
