# 电子书阅读器进度同步路由
# 设计：本地文件阅读（文件不上传服务器），云端仅按内容哈希(book_key)同步阅读进度，
# 同一用户同一本书（book_key 唯一），支持跨设备续读。进度 upsert，防越权（仅本人）。
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ReadingRecord, User
from app.schemas import (
    ApiResponse,
    ApiListResponse,
    ProgressSaveRequest,
    ReadingRecordResponse,
)
from app.auth.deps import get_current_user

router = APIRouter(
    prefix="/api/v1/reader",
    tags=["阅读器进度"],
)

# book_key 为本地文件内容 SHA-256（64 位十六进制）
_BOOK_KEY_RE = re.compile(r"^[0-9a-f]{64}$")


def _check_book_key(book_key: str) -> str:
    key = book_key.strip().lower()
    if not _BOOK_KEY_RE.fullmatch(key):
        raise HTTPException(status_code=400, detail="book_key 非法（应为内容 SHA-256）")
    return key


async def _get_record(
    session: AsyncSession, user: User, book_key: str
) -> ReadingRecord:
    """获取当前用户的进度记录（不存在 → 404，防越权：按 user_id 限定）"""
    row = (await session.execute(
        select(ReadingRecord).where(
            ReadingRecord.user_id == user.id,
            ReadingRecord.book_key == book_key,
        )
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="暂无该书的进度记录")
    return row


def _to_response(r: ReadingRecord) -> ReadingRecordResponse:
    return ReadingRecordResponse(
        id=r.id,
        book_key=r.book_key,
        title=r.title,
        author=r.author,
        format=r.format,
        progress=r.progress,
        progress_total=r.progress_total,
        updated_at=r.updated_at,
    )


@router.put("/progress", response_model=ApiResponse)
async def save_progress(
    req: ProgressSaveRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """保存/更新阅读进度（按 book_key upsert）。文件留在本地，云端只存进度。"""
    book_key = _check_book_key(req.book_key)

    row = (await session.execute(
        select(ReadingRecord).where(
            ReadingRecord.user_id == current_user.id,
            ReadingRecord.book_key == book_key,
        )
    )).scalar_one_or_none()

    if row is None:
        row = ReadingRecord(
            user_id=current_user.id,
            book_key=book_key,
            title=req.title.strip() or "未命名书籍",
            author=req.author.strip(),
            format=req.format,
            progress=req.progress,
            progress_total=req.progress_total,
        )
        session.add(row)
    else:
        row.title = req.title.strip() or row.title
        row.author = req.author.strip()
        row.format = req.format
        row.progress = req.progress
        row.progress_total = req.progress_total

    await session.commit()
    return ApiResponse(data={"book_key": book_key}, message="进度已保存")


@router.get("/progress/{book_key}", response_model=ApiResponse)
async def get_progress(
    book_key: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """读取指定书（按 book_key）的进度"""
    key = _check_book_key(book_key)
    row = await _get_record(session, current_user, key)
    return ApiResponse(data={"position": row.progress, "total": row.progress_total})


@router.get("/history", response_model=ApiListResponse[ReadingRecordResponse])
async def list_history(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """阅读历史（最近阅读在前，含进度与最后阅读时间）"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 20

    total = (await session.execute(
        select(func.count(ReadingRecord.id)).where(
            ReadingRecord.user_id == current_user.id
        )
    )).scalar()

    rows = (await session.execute(
        select(ReadingRecord)
        .where(ReadingRecord.user_id == current_user.id)
        .order_by(ReadingRecord.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    return ApiListResponse(data=[_to_response(r) for r in rows], total=total or 0)


@router.delete("/history/{book_key}", response_model=ApiResponse)
async def delete_record(
    book_key: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """删除一条阅读记录（仅云端进度；本地文件不受影响）"""
    key = _check_book_key(book_key)
    row = await _get_record(session, current_user, key)
    await session.delete(row)
    await session.commit()
    return ApiResponse(data=None, message="已删除")
