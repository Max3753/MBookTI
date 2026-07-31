# 个人通知模型（评论获赞 / 管理员消息）
from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base


class Notification(Base):
    """个人通知收件箱。

    type: 1=评论获赞(like)  2=管理员消息(admin_message)
    3=评论被回复(reply)（预留，暂未触发）
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[int] = mapped_column(SmallInteger, default=1)
    content: Mapped[str] = mapped_column(String(500))
    related_book_id: Mapped[int] = mapped_column(Integer, nullable=True)
    related_comment_id: Mapped[int] = mapped_column(Integer, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
