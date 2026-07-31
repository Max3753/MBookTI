from datetime import datetime
from typing import Optional
from pydantic import BaseModel

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
    created_at: datetime
    book: RecommendationBook

    model_config = {"from_attributes": True}


class AIGenerateRequest(BaseModel):
    mbti_code: str
    count: int = 5


class AIGenerateBook(BaseModel):
    title: str
    author: str
    description: str
    reasoning: str
    genre: str
