# books 数据库 ROM 类
from sqlalchemy import Integer, String, Text, JSON, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base

class Book(Base):
    __tablename__ = "books"
    # 数据库层防重复：同名同作者不允许重复入库（isbn 由 AI 生成从不写入，唯一约束空转，
    # 故以 (title, author) 作为真实去重键。应用层 _normalize_book 规范化匹配与此互补：
    # 约束防「字符串完全一致」的重复，规范化查重防《》/空格等细微变体）。
    __table_args__ = (
        UniqueConstraint("title", "author", name="uq_books_title_author"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[str] = mapped_column(String(255))
    isbn: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="zh")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
