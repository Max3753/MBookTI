# user 数据库模型
from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, String, Text, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional
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
    # 公开主页开关：True=任何人可查看我的主页/书评/收藏/粉丝列表；False=仅自己可见（默认公开，向后兼容）
    is_profile_public: Mapped[bool] = mapped_column(Boolean, default=True)
    # 最近一次密码修改时间：非空时要求访问 token 的签发时间(iat)不早于它，用于改密后使旧 token 立即失效
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
