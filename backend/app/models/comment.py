# comment 数据库模型
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base

class Comment(Base):
    __tablename__ = "comments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    # 书评：挂到书，跨 MBTI 类型聚合
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("books.id"))
    # 兼容旧数据（历史评论的推荐上下文），新评论不再使用
    recommendation_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recommendations.id"), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("comments.id"))
    content: Mapped[str] = mapped_column(Text)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
