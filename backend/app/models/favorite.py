# user_book_favorites 数据库模型（用户收藏书籍）
from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base


class UserBookFavorite(Base):
    __tablename__ = "user_book_favorites"
    __table_args__ = (
        # 同一用户对同一本书只允许一条收藏（防并发重复数据）
        UniqueConstraint("user_id", "book_id", name="uq_user_book"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("books.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
