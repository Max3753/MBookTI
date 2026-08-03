from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.datetime_utils import UtcDatetime

class RecommendationBook(BaseModel):
    """推荐中返回的书籍信息(精简)"""
    id: int
    title: str
    author: str
    cover_url: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    
class RecommendationResponse(BaseModel):
    id: int
    reasoning: str
    relevance_score: int
    is_ai_generated: bool
    likes_count: int
    created_at: UtcDatetime
    book: RecommendationBook

    model_config = {"from_attributes": True}


class AIGenerateRequest(BaseModel):
    mbti_code: str = Field(min_length=4, max_length=4, pattern=r"^[A-Za-z]{4}$")
    count: int = Field(default=5, ge=1, le=10)  # 上限 10 本：防止 count 滥用导致巨额 AI 费用/大量豆瓣请求


class AIGenerateBook(BaseModel):
    title: str
    author: str
    description: str
    reasoning: str
    genre: str
