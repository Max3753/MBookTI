# 社区动态（Feed）路由：聚合最新书评与收藏，按时间倒序合并展示
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book, Comment, User, UserBookFavorite
from app.schemas import ApiResponse, FeedItem

router = APIRouter(
    prefix="/api/v1/community",
    tags=["社区"],
)


@router.get("/feed", response_model=ApiResponse[list[FeedItem]])
async def community_feed(
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
):
    """社区动态：最新书评 + 最新收藏合并，按 created_at 倒序，取前 limit 条。

    comment 类型条目携带 comment_id/content/parent_id；favorite 类型这些字段为 None。
    """
    if limit < 1:
        limit = 20
    if limit > 100:
        limit = 100

    # 最新 limit 条书评（隐藏的、以及关闭公开主页的用户不对外展示）
    comment_rows = (await session.execute(
        select(Comment, User, Book)
        .join(User, Comment.user_id == User.id)
        .join(Book, Comment.book_id == Book.id)
        .where(
            Comment.is_hidden == False,  # noqa: E712
            User.is_profile_public == True,  # noqa: E712
        )
        .order_by(Comment.created_at.desc())
        .limit(limit)
    )).all()

    # 最新 limit 条收藏（关闭公开主页的用户不出现在动态流）
    fav_rows = (await session.execute(
        select(UserBookFavorite, User, Book)
        .join(User, UserBookFavorite.user_id == User.id)
        .join(Book, UserBookFavorite.book_id == Book.id)
        .where(User.is_profile_public == True)  # noqa: E712
        .order_by(UserBookFavorite.created_at.desc())
        .limit(limit)
    )).all()

    # 两种类型各自取 limit 条，合并后在 Python 端排序截断
    items: list[FeedItem] = []
    for c, u, b in comment_rows:
        items.append(FeedItem(
            type="comment",
            id=c.id,
            user_id=c.user_id,
            username=u.username,
            avatar_url=u.avatar_url,
            created_at=c.created_at,
            book_id=c.book_id,
            book_title=b.title,
            book_cover_url=b.cover_url,
            comment_id=c.id,
            content=c.content,
            parent_id=c.parent_id,
        ))
    for f, u, b in fav_rows:
        items.append(FeedItem(
            type="favorite",
            id=f.id,
            user_id=f.user_id,
            username=u.username,
            avatar_url=u.avatar_url,
            created_at=f.created_at,
            book_id=f.book_id,
            book_title=b.title,
            book_cover_url=b.cover_url,
            comment_id=None,
            content=None,
            parent_id=None,
        ))

    items.sort(key=lambda x: x.created_at, reverse=True)
    return ApiResponse(data=items[:limit])
