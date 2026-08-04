# reading_records 数据库模型（阅读进度云端同步记录）
# 设计：本地文件不上传服务器，云端仅按内容哈希(book_key)保存阅读进度与元信息，
# 同一用户同一本书（book_key 唯一），反复阅读时 upsert 更新，支持跨设备续读。
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base


class ReadingRecord(Base):
    __tablename__ = "reading_records"
    __table_args__ = (
        UniqueConstraint("user_id", "book_key", name="uq_reading_records_user_book"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 归属用户（进度私有，仅本人可见）
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    # 本地文件内容 SHA-256（64 位十六进制），作为唯一稳定标识（同名不同文件互不干扰）
    book_key: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255), default="")
    format: Mapped[str] = mapped_column(String(10), default="txt")  # txt / epub / pdf
    # 阅读进度：按格式存 JSON（TXT=段落号 / EPUB=CFI / PDF=页码），原样存储
    progress: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # 总页/段/章数（UI 显示进度百分比用；EPUB=章节数，PDF=页数，TXT=段落数）
    progress_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
