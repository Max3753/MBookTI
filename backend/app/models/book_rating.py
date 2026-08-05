# book_ratings 数据库模型（用户对书籍的 1-5 星评分）
from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base


class BookRating(Base):
    __tablename__ = "book_ratings"
    __table_args__ = (
        # 同一用户对同一本书只允许一条评分（upsert 语义）
        UniqueConstraint("user_id", "book_id", name="uq_user_book_rating"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("books.id"))
    # 1-5 星（请求体校验范围，DB 层不再约束）
    rating: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
