# user 数据库模型
from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, String, Text, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str] = mapped_column(Text, nullable=True)
    mbti_type_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("mbti_types.id") ,nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
