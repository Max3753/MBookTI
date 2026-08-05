# user_follows 数据库模型（用户关注关系：follower 关注 following）
from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base


class UserFollow(Base):
    __tablename__ = "user_follows"
    __table_args__ = (
        # 同一关注关系只允许一条（防并发重复数据）
        UniqueConstraint("follower_id", "following_id", name="uq_user_follow"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 关注者（发起关注的一方）
    follower_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    # 被关注者
    following_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
