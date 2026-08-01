# 用户个人中心路由
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book, Comment, MbtiType, User, UserBookFavorite
from app.schemas import (
    AdminResetPasswordRequest,
    ApiListResponse,
    ApiResponse,
    BookResponse,
    ChangePasswordRequest,
    MyCommentResponse,
    UserProfileResponse,
    UserStats,
    UserUpdateRequest,
    UserResponse,
)
from app.auth.deps import get_current_user, get_current_admin
from app.auth.password import hash_password, verify_password

router = APIRouter(
    prefix="/api/v1/users",
    tags=["用户"],
)


@router.get("/me", response_model=ApiResponse[UserProfileResponse])
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    # join mbti_types 取 code/name（outerjoin：用户可能未设置 MBTI）
    result = await session.execute(
        select(User, MbtiType)
        .outerjoin(MbtiType, User.mbti_type_id == MbtiType.id)
        .where(User.id == current_user.id)
    )
    row = result.first()
    user, mbti = (row[0], row[1]) if row else (current_user, None)

    # 统计
    comment_count = (
        await session.execute(
            select(func.count(Comment.id)).where(Comment.user_id == current_user.id)
        )
    ).scalar()
    like_received = (
        await session.execute(
            select(func.coalesce(func.sum(Comment.likes_count), 0)).where(
                Comment.user_id == current_user.id
            )
        )
    ).scalar()
    favorite_count = (
        await session.execute(
            select(func.count(UserBookFavorite.id)).where(
                UserBookFavorite.user_id == current_user.id
            )
        )
    ).scalar()

    return ApiResponse(data=UserProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        avatar_url=user.avatar_url,
        mbti_type_id=user.mbti_type_id,
        mbti_type_code=mbti.code if mbti else None,
        mbti_type_name=mbti.name if mbti else None,
        is_admin=user.is_admin,
        created_at=user.created_at,
        stats=UserStats(
            comment_count=comment_count or 0,
            favorite_count=favorite_count or 0,
            like_received=like_received or 0,
        ),
    ))

@router.put("/me", response_model=ApiResponse[UserProfileResponse])
async def update_me(
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    data = req.model_dump(exclude_unset=True)

    # 用户名唯一性校验（改名时）
    new_username = data.get("username")
    if new_username and new_username != current_user.username:
        exists = (
            await session.execute(select(User).where(User.username == new_username))
        ).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=400, detail="用户名已存在")

    # MBTI 类型存在性校验（避免外键约束失败导致 500）
    new_mbti_type_id = data.get("mbti_type_id")
    if new_mbti_type_id is not None:
        mbti = (
            await session.execute(select(MbtiType).where(MbtiType.id == new_mbti_type_id))
        ).scalar_one_or_none()
        if mbti is None:
            raise HTTPException(status_code=400, detail="MBTI 类型不存在")

    for field, value in data.items():
        setattr(current_user, field, value)

    await session.commit()
    await session.refresh(current_user)

    # 重新组装（含 MBTI 信息 + 统计）
    result = await session.execute(
        select(User, MbtiType)
        .outerjoin(MbtiType, User.mbti_type_id == MbtiType.id)
        .where(User.id == current_user.id)
    )
    row = result.first()
    user, mbti = (row[0], row[1]) if row else (current_user, None)
    comment_count = (
        await session.execute(
            select(func.count(Comment.id)).where(Comment.user_id == current_user.id)
        )
    ).scalar()
    like_received = (
        await session.execute(
            select(func.coalesce(func.sum(Comment.likes_count), 0)).where(
                Comment.user_id == current_user.id
            )
        )
    ).scalar()
    favorite_count = (
        await session.execute(
            select(func.count(UserBookFavorite.id)).where(
                UserBookFavorite.user_id == current_user.id
            )
        )
    ).scalar()

    return ApiResponse(data=UserProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        avatar_url=user.avatar_url,
        mbti_type_id=user.mbti_type_id,
        mbti_type_code=mbti.code if mbti else None,
        mbti_type_name=mbti.name if mbti else None,
        is_admin=user.is_admin,
        created_at=user.created_at,
        stats=UserStats(
            comment_count=comment_count or 0,
            favorite_count=favorite_count or 0,
            like_received=like_received or 0,
        ),
    ))


@router.put("/me/password", response_model=ApiResponse)
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")

    current_user.password_hash = hash_password(req.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
    await session.commit()
    return ApiResponse(data=None, message="密码已修改")


@router.get("/me/comments", response_model=ApiListResponse[MyCommentResponse])
async def my_comments(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 20

    result = await session.execute(
        select(Comment, Book)
        .join(Book, Comment.book_id == Book.id)
        .where(Comment.user_id == current_user.id)
        .order_by(Comment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.all()

    total = (
        await session.execute(
            select(func.count(Comment.id)).where(Comment.user_id == current_user.id)
        )
    ).scalar()

    items = [
        MyCommentResponse(
            id=c.id,
            book_id=c.book_id,
            book_title=b.title,
            book_cover_url=b.cover_url,
            parent_id=c.parent_id,
            content=c.content,
            likes_count=c.likes_count,
            created_at=c.created_at,
        )
        for c, b in rows
    ]
    return ApiListResponse(data=items, total=total or 0)


@router.post("/me/favorites/{book_id}", response_model=ApiResponse)
async def toggle_favorite(
    book_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    # 书必须存在
    book = (
        await session.execute(select(Book).where(Book.id == book_id))
    ).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    exists = (
        await session.execute(
            select(UserBookFavorite).where(
                UserBookFavorite.user_id == current_user.id,
                UserBookFavorite.book_id == book_id,
            )
        )
    ).scalar_one_or_none()

    if exists:
        await session.delete(exists)
        is_favorited = False
    else:
        session.add(UserBookFavorite(user_id=current_user.id, book_id=book_id))
        is_favorited = True

    await session.commit()
    return ApiResponse(data={"is_favorited": is_favorited})


@router.get("/me/favorites", response_model=ApiListResponse[BookResponse])
async def my_favorites(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(Book)
        .join(UserBookFavorite, UserBookFavorite.book_id == Book.id)
        .where(UserBookFavorite.user_id == current_user.id)
        .order_by(UserBookFavorite.created_at.desc())
    )
    books = result.scalars().all()
    return ApiListResponse(data=[BookResponse.model_validate(b) for b in books], total=len(books))


@router.get("", response_model=ApiListResponse[UserResponse])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """管理员：分页查看所有用户。"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 20

    total = (
        await session.execute(select(func.count(User.id)))
    ).scalar()

    result = await session.execute(
        select(User)
        .order_by(User.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()
    return ApiListResponse(
        data=[UserResponse.model_validate(u) for u in users],
        total=total or 0,
    )


@router.put("/{user_id}/password", response_model=ApiResponse)
async def admin_reset_password(
    user_id: str,
    req: AdminResetPasswordRequest,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """管理员重置指定用户密码。更新 password_changed_at 使该用户所有旧 token 立即失效。

    注意：user_id 为 "me" 时与 PUT /users/me/password 语义冲突，直接 404。
    """
    if user_id == "me":
        raise HTTPException(status_code=404, detail="用户不存在")

    try:
        uid = int(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="用户不存在")

    user = (
        await session.execute(select(User).where(User.id == uid))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.password_hash = hash_password(req.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    await session.commit()
    return ApiResponse(data=None, message=f"已重置用户 {user.username} 的密码")
