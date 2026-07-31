# user_book_favorites 数据库模型（用户收藏书籍）
from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base


class UserBookFavorite(Base):
    __tablename__ = "user_book_favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("books.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
