from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book, Recommendation, MbtiType, Comment, User, UserBookFavorite, BookRating
from app.schemas import (
    ApiResponse,
    ApiListResponse,
    BookResponse,
    BookDetailResponse,
    RecommendedTypeInfo,
    BookRatingRequest,
    BookRatingResponse,
)
from app.auth.deps import get_current_user_optional, get_current_user

router = APIRouter(
    prefix="/api/v1/books",
    tags=["书目"]
)

# 注意：/search 必须声明在 /{book_id} 之前，否则会被 int 路径参数路由吞掉
@router.get("/search", response_model=ApiListResponse[BookResponse])
async def search_books(
    q: str,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db),
):
    """站内书籍搜索：q 模糊匹配书名/作者（LIKE），命中 ISBN 精确匹配；分页返回。"""
    keyword = (q or "").strip()
    if not keyword:
        return ApiListResponse(data=[], total=0, message="请输入搜索关键词")

    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 20

    # 模糊匹配书名/作者（前导通配符不走索引，books 量小全表扫可接受）
    like_pattern = f"%{keyword}%"
    from sqlalchemy import or_
    conditions = [
        Book.title.like(like_pattern),
        Book.author.like(like_pattern),
    ]
    # ISBN 精确匹配（走唯一索引）
    conditions.append(Book.isbn == keyword)

    total = (
        await session.execute(select(func.count(Book.id)).where(or_(*conditions)))
    ).scalar()

    result = await session.execute(
        select(Book)
        .where(or_(*conditions))
        .order_by(Book.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    books = result.scalars().all()
    return ApiListResponse(
        data=[BookResponse.model_validate(b) for b in books],
        total=total or 0,
    )

@router.get("/{book_id}", response_model=ApiResponse[BookResponse])
async def get_book(book_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="未找到书目")
    return ApiResponse(data=book)


@router.get("/{book_id}/detail", response_model=ApiResponse[BookDetailResponse])
async def get_book_detail(
    book_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    result = await session.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="未找到书目")

    # 被哪些 MBTI 类型推荐（去重）
    type_rows = await session.execute(
        select(MbtiType.code, MbtiType.name)
        .join(Recommendation, Recommendation.mbti_type_id == MbtiType.id)
        .where(Recommendation.book_id == book_id)
        .distinct()
    )
    recommended_types = [RecommendedTypeInfo(code=code, name=name) for code, name in type_rows.all()]

    # 评论数
    comment_count = (await session.execute(
        select(func.count()).select_from(Comment).where(Comment.book_id == book_id)
    )).scalar()

    # 当前用户是否收藏
    is_favorited = False
    if current_user is not None:
        fav = (await session.execute(
            select(UserBookFavorite).where(
                UserBookFavorite.user_id == current_user.id,
                UserBookFavorite.book_id == book_id,
            )
        )).scalar_one_or_none()
        is_favorited = fav is not None

    # 评分汇总：平均分保留 1 位小数；无评分时 avg_rating 为 None
    rating_row = (await session.execute(
        select(
            func.avg(BookRating.rating),
            func.count(BookRating.id),
        ).where(BookRating.book_id == book_id)
    )).first()
    avg_rating = round(float(rating_row[0]), 1) if rating_row and rating_row[0] is not None else None
    rating_count = rating_row[1] or 0

    # 当前用户自己的评分（未登录时 my_rating 为 None）
    my_rating = None
    if current_user is not None:
        my_rating = (await session.execute(
            select(BookRating.rating).where(
                BookRating.user_id == current_user.id,
                BookRating.book_id == book_id,
            )
        )).scalar_one_or_none()

    detail = BookDetailResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        cover_url=book.cover_url,
        description=book.description,
        genre=book.genre,
        recommended_types=recommended_types,
        comment_count=comment_count,
        is_favorited=is_favorited,
        avg_rating=avg_rating,
        rating_count=rating_count,
        my_rating=my_rating,
        created_at=book.created_at,
    )
    return ApiResponse(data=detail)


@router.post("/{book_id}/rating", response_model=ApiResponse[BookRatingResponse])
async def upsert_rating(
    book_id: int,
    req: BookRatingRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """评分/改分（upsert：同一用户同一本书仅一条记录）。评分范围 1-5 由请求体 Field 校验。"""
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="未找到书目")

    existing = (await session.execute(
        select(BookRating).where(
            BookRating.user_id == current_user.id,
            BookRating.book_id == book_id,
        )
    )).scalar_one_or_none()

    if existing:
        # 已评分则更新为最新分数（唯一约束保证单条）
        existing.rating = req.rating
    else:
        session.add(BookRating(user_id=current_user.id, book_id=book_id, rating=req.rating))
    await session.commit()
    return ApiResponse(data=BookRatingResponse(rating=req.rating))


@router.delete("/{book_id}/rating", response_model=ApiResponse[BookRatingResponse])
async def delete_rating(
    book_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """取消自己的评分（幂等：未评分也返回成功，rating 为 None）。"""
    existing = (await session.execute(
        select(BookRating).where(
            BookRating.user_id == current_user.id,
            BookRating.book_id == book_id,
        )
    )).scalar_one_or_none()
    if existing:
        await session.delete(existing)
        await session.commit()
    return ApiResponse(data=BookRatingResponse(rating=None))
