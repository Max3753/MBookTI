# 阅读器进度同步相关请求/响应模型
from typing import Literal, Optional
from pydantic import BaseModel, Field
from app.schemas.datetime_utils import UtcDatetime


class ProgressSaveRequest(BaseModel):
    """保存阅读进度：book_key 为本地文件内容 SHA-256，progress 为按格式的 JSON 字符串"""
    book_key: str = Field(..., min_length=64, max_length=64)
    title: str = Field(..., max_length=255)
    author: str = Field("", max_length=255)
    format: Literal["txt", "epub", "pdf"] = "txt"
    progress: Optional[str] = None
    progress_total: Optional[int] = None


class ReadingRecordResponse(BaseModel):
    """阅读记录条目（阅读历史列表）"""
    id: int
    book_key: str
    title: str
    author: str
    format: str
    progress: Optional[str] = None
    progress_total: Optional[int] = None
    updated_at: UtcDatetime

    model_config = {"from_attributes": True}
