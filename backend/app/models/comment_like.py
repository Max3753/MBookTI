# comment_like 数据库模型
from sqlalchemy import ForeignKey, Integer, String, Text, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base

class CommentLike(Base):
    __tablename__ = 'comment_likes'
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), primary_key=True)
    comment_id: Mapped[int] = mapped_column(Integer, ForeignKey('comments.id'), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
