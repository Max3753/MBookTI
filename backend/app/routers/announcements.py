# 系统公告路由：主页弹窗推送 + 确认（ack）
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Announcement, AnnouncementAck, User
from app.schemas import (
    ApiListResponse,
    ApiResponse,
    AnnouncementCreateRequest,
    AnnouncementResponse,
)
from app.auth.deps import get_current_user, get_current_user_optional, get_current_admin

router = APIRouter(
    prefix="/api/v1/announcements",
    tags=["系统公告"],
)


async def _ack_exists(session: AsyncSession, announcement_id: int, user_id: int) -> bool:
    exists = (
        await session.execute(
            select(AnnouncementAck.id).where(
                AnnouncementAck.announcement_id == announcement_id,
                AnnouncementAck.user_id == user_id,
            )
        )
    ).first()
    return exists is not None


@router.get("/unacked", response_model=ApiListResponse[AnnouncementResponse])
async def get_unacked_announcements(
    current_user: User | None = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_db),
):
    """主页弹窗：返回 active 且当前用户未确认的公告（最多 3 条）。

    未登录用户返回全部 active 公告（前端用 sessionStorage 记录本次会话已看）。
    """
    result = await session.execute(
        select(Announcement)
        .where(Announcement.is_active.is_(True))
        .order_by(Announcement.created_at.desc())
        .limit(50)
    )
    announcements = result.scalars().all()

    if current_user is None:
        items = [a for a in announcements[:3]]
        return ApiListResponse(
            data=[AnnouncementResponse.model_validate(a) for a in items],
            total=len(items),
        )

    unacked = []
    for a in announcements:
        if len(unacked) >= 3:
            break
        if not await _ack_exists(session, a.id, current_user.id):
            unacked.append(a)
    return ApiListResponse(
        data=[AnnouncementResponse.model_validate(a) for a in unacked],
        total=len(unacked),
    )


@router.post("/{announcement_id}/ack", response_model=ApiResponse)
async def ack_announcement(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """确认公告：标记已读，之后不再推送。"""
    ann = (
        await session.execute(
            select(Announcement).where(Announcement.id == announcement_id)
        )
    ).scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")

    if await _ack_exists(session, announcement_id, current_user.id):
        return ApiResponse(data=None, message="已确认")

    session.add(AnnouncementAck(
        announcement_id=announcement_id,
        user_id=current_user.id,
    ))
    await session.commit()
    return ApiResponse(data=None, message="已确认")


# ---------- 管理员 ----------

@router.post("", response_model=ApiResponse[AnnouncementResponse])
async def create_announcement(
    req: AnnouncementCreateRequest,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """发布系统公告（广播给所有用户）。"""
    ann = Announcement(
        title=req.title,
        content=req.content,
        is_active=True,
        created_by=admin.id,
    )
    session.add(ann)
    await session.commit()
    await session.refresh(ann)
    return ApiResponse(data=AnnouncementResponse.model_validate(ann))


@router.get("", response_model=ApiListResponse[AnnouncementResponse])
async def list_announcements(
    page: int = 1,
    page_size: int = 20,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """管理列表（含已下线）。"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 20

    total = (await session.execute(select(func.count(Announcement.id)))).scalar()
    result = await session.execute(
        select(Announcement)
        .order_by(Announcement.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()
    return ApiListResponse(
        data=[AnnouncementResponse.model_validate(a) for a in items],
        total=total or 0,
    )


@router.delete("/{announcement_id}", response_model=ApiResponse)
async def deactivate_announcement(
    announcement_id: int,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """下线公告（逻辑删除：is_active=False，不再推送）。"""
    ann = (
        await session.execute(
            select(Announcement).where(Announcement.id == announcement_id)
        )
    ).scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")

    ann.is_active = False
    await session.commit()
    return ApiResponse(data=None, message="已下线")
