# 系统公告模型
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base


class Announcement(Base):
    """系统公告：主页弹窗强提醒，用户确认（ack）后不再展示。"""

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AnnouncementAck(Base):
    """公告确认记录：announcement_id + user_id 唯一，已确认的公告不再推送。"""

    __tablename__ = "announcement_acks"
    __table_args__ = (
        # 同用户对同公告只允许一条确认（防并发重复）
        UniqueConstraint("announcement_id", "user_id", name="uq_announcement_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    announcement_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("announcements.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    acked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
