# 忘记密码一次性重置令牌模型
# 只存 token 的 sha256 哈希（token_hash），绝不存明文；
# 明文 token 仅通过邮件（或 dev 模式响应）一次性交给用户，校验时 sha256(token) 查库。
from sqlalchemy import CHAR, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional

from app.models.base import Base


class PasswordResetToken(Base):
    """忘记密码重置令牌。

    token_hash: sha256(明文 token) 的 hex 字符串（固定 64 字符，CHAR(64)）
    expires_at: 过期时间，过期后视为无效
    used_at:    使用时间，非空表示已用（一次性令牌）
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
