from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None
    cover_url: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    language: str = "zh"
    created_at: datetime
    
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
    created_at: datetime

    model_config = {"from_attributes": True}
