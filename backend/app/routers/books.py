from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book, Recommendation, MbtiType, Comment
from app.schemas import ApiResponse, BookResponse, BookDetailResponse, RecommendedTypeInfo

router = APIRouter(
    prefix="/api/v1/books",
    tags=["书目"]
)

@router.get("/{book_id}", response_model=ApiResponse[BookResponse])
async def get_book(book_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="未找到书目")
    return ApiResponse(data=book)


@router.get("/{book_id}/detail", response_model=ApiResponse[BookDetailResponse])
async def get_book_detail(book_id: int, session: AsyncSession = Depends(get_db)):
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

    detail = BookDetailResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        cover_url=book.cover_url,
        description=book.description,
        genre=book.genre,
        recommended_types=recommended_types,
        comment_count=comment_count,
        created_at=book.created_at,
    )
    return ApiResponse(data=detail)
