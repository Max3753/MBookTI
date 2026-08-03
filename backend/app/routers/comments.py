from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book, Comment, CommentLike, Notification, User
from app.schemas import ApiResponse, ApiListResponse
from app.schemas.comment import CommentCreateRequest, CommentResponse
from app.auth.deps import get_current_user

router = APIRouter(
    prefix="/api/v1/comments",
    tags=["评论"],
)


@router.post("", response_model=ApiResponse[CommentResponse])
async def create_comment(
    req: CommentCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 书必须存在（避免外键约束失败导致 500 / 孤儿评论）
    book = await session.get(Book, req.book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    # 父评论校验：存在、且与子评论挂同一本书（避免跨书挂回复）
    if req.parent_id is not None:
        parent = await session.get(Comment, req.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="父评论不存在")
        if parent.book_id != req.book_id:
            raise HTTPException(status_code=400, detail="父评论与当前书籍不匹配")

    comment = Comment(
        user_id=current_user.id,
        book_id=req.book_id,
        content=req.content,
        parent_id=req.parent_id,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    resp = CommentResponse(
        id=comment.id,
        user_id=comment.user_id,
        username=current_user.username,
        avatar_url=current_user.avatar_url,
        book_id=comment.book_id,
        parent_id=comment.parent_id,
        content=comment.content,
        likes_count=comment.likes_count,
        is_edited=comment.is_edited,
        created_at=comment.created_at,
    )
    return ApiResponse(data=resp)


@router.get("/book/{book_id}", response_model=ApiListResponse[CommentResponse])
async def list_book_comments(book_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(Comment, User)
        .join(User, Comment.user_id == User.id)
        .where(Comment.book_id == book_id, Comment.is_hidden == False)
        .order_by(Comment.created_at.asc())
    )
    rows = result.all()

    data = []
    for c, u in rows:
        data.append(CommentResponse(
            id=c.id,
            user_id=c.user_id,
            username=u.username,
            avatar_url=u.avatar_url,
            book_id=c.book_id,
            parent_id=c.parent_id,
            content=c.content,
            likes_count=c.likes_count,
            is_edited=c.is_edited,
            created_at=c.created_at,
        ))
    return ApiListResponse(data=data, total=len(data))


@router.post("/{comment_id}/like", response_model=ApiResponse)
async def toggle_like(
    comment_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 检查评论是否存在
    comment = await session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    # 检查是否已点赞
    existing = await session.execute(
        select(CommentLike).where(
            CommentLike.user_id == current_user.id,
            CommentLike.comment_id == comment_id,
        )
    )
    like = existing.scalar_one_or_none()

    if like:
        await session.delete(like)
        comment.likes_count = max(0, comment.likes_count - 1)
        await session.commit()
        return ApiResponse(data={"liked": False, "likes_count": comment.likes_count})
    else:
        session.add(CommentLike(user_id=current_user.id, comment_id=comment_id))
        comment.likes_count += 1
        # 获赞通知：非自己赞自己时，给被赞者发通知（含跳转书籍信息）
        # 同一用户对同一评论的赞只通知一次（取消再赞不重复）
        if comment.user_id != current_user.id:
            dup = await session.execute(
                select(Notification).where(
                    Notification.user_id == comment.user_id,
                    Notification.type == 1,
                    Notification.related_comment_id == comment.id,
                )
            )
            if dup.scalar_one_or_none() is None:
                session.add(Notification(
                    user_id=comment.user_id,
                    type=1,  # 评论获赞
                    content=f"你的书评被 {current_user.username} 赞了",
                    related_book_id=comment.book_id,
                    related_comment_id=comment.id,
                ))
        await session.commit()
        return ApiResponse(data={"liked": True, "likes_count": comment.likes_count})


@router.delete("/{comment_id}", response_model=ApiResponse)
async def delete_comment(
    comment_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除自己的书评（硬删，同时清理点赞记录、子评论及相关通知）"""
    comment = await session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除他人评论")

    # 清理该评论及其子评论的点赞记录
    await session.execute(
        delete(CommentLike).where(CommentLike.comment_id == comment_id)
    )
    # 子评论（parent_id 指向本评论）一并删除，避免外键约束报错
    child_ids = (
        await session.execute(
            select(Comment.id).where(Comment.parent_id == comment_id)
        )
    ).scalars().all()
    if child_ids:
        await session.execute(
            delete(CommentLike).where(CommentLike.comment_id.in_(child_ids))
        )
        await session.execute(
            delete(Comment).where(Comment.id.in_(child_ids))
        )
    # 清理相关获赞通知（避免残留指向已删除评论的通知）
    await session.execute(
        delete(Notification).where(Notification.related_comment_id == comment_id)
    )
    await session.delete(comment)
    await session.commit()
    return ApiResponse(data=None, message="评论已删除")
