# 个人通知路由：评论获赞 / 管理员消息
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Notification, User
from app.schemas import (
    ApiListResponse,
    ApiResponse,
    NotificationCreateRequest,
    NotificationResponse,
    UnreadCountResponse,
)
from app.auth.deps import get_current_user, get_current_admin

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["通知"],
)

TYPE_LIKE = 1
TYPE_ADMIN_MESSAGE = 2


@router.get("", response_model=ApiListResponse[NotificationResponse])
async def list_notifications(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """我的通知收件箱（分页，最新在前）。"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 20

    total = (
        await session.execute(
            select(func.count(Notification.id)).where(Notification.user_id == current_user.id)
        )
    ).scalar()

    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()
    return ApiListResponse(
        data=[NotificationResponse.model_validate(n) for n in items],
        total=total or 0,
    )


@router.get("/unread-count", response_model=ApiResponse[UnreadCountResponse])
async def unread_count(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """未读数（导航栏红点）。"""
    unread = (
        await session.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == current_user.id,
                Notification.is_read == False,  # noqa: E712
            )
        )
    ).scalar()
    return ApiResponse(data=UnreadCountResponse(unread=unread or 0))


@router.post("/{notification_id}/read", response_model=ApiResponse)
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """标记单条已读（仅本人）。"""
    n = (
        await session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")
    if not n.is_read:
        n.is_read = True
        await session.commit()
    return ApiResponse(data=None, message="已读")


@router.post("/read-all", response_model=ApiResponse)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """全部标记已读。"""
    await session.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await session.commit()
    return ApiResponse(data=None, message="全部已读")


# ---------- 管理员 ----------

@router.post("/to/{user_id}", response_model=ApiResponse)
async def send_admin_message(
    user_id: int,
    req: NotificationCreateRequest,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """管理员定向发送消息。"""
    target = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    session.add(Notification(
        user_id=user_id,
        type=TYPE_ADMIN_MESSAGE,
        content=req.content,
    ))
    await session.commit()
    return ApiResponse(data=None, message="已发送")
