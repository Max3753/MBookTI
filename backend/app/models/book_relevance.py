# book_relevance 数据库模型（书籍 × MBTI 类型的 AI 相关度评分缓存）
from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base


class BookRelevance(Base):
    __tablename__ = "book_relevance"
    __table_args__ = (
        # 同一本书对同一 MBTI 类型只允许一条评分记录（首个 AI 评分永久缓存，保证跨批次恒定）
        UniqueConstraint("book_id", "mbti_type_id", name="uq_book_relevance"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("books.id"), index=True)
    mbti_type_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("mbti_types.id"), index=True)
    # 0-10 整数：AI 首次推荐该书时评出的相关度，此后固定复用
    relevance_score: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
