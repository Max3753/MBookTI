# recommendations数据库 ROM 类
from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, String, Text, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mbti_type_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("mbti_types.id"))
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("books.id"))
    reasoning: Mapped[str] = mapped_column(Text)
    relevance_score: Mapped[int] = mapped_column(SmallInteger, default=5)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
