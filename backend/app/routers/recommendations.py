from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MbtiType, Book, Recommendation, User
from app.schemas import ApiResponse, AIGenerateRequest, RecommendationResponse
from app.auth.deps import get_current_user
from app.services.douban import search_cover

router = APIRouter(
    prefix="/api/v1/recommendations",
    tags=["推荐"],
)


def _normalize_book(s: str) -> str:
    """书籍查重用规范化：去掉书名号/空格/连字符/标点等。

    AI 生成的 title/author 常带细微差异（《》、-、· 等），
    精确匹配必然查不到已有书籍导致重复入库，故统一归一化后比较。
    """
    import re
    return re.sub(r"[\s《》·\-—:：,，.。\"'“”]+", "", s or "")

@router.post("/ai-generate", response_model=ApiResponse)
async def ai_generate(
    request: AIGenerateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  # 需登录：防止匿名刷接口造成 AI 费用滥用
):
    type_result = await session.execute(
        select(MbtiType).where(MbtiType.code == request.mbti_code.upper())
    )
    mbti_type = type_result.scalar_one_or_none()
    if not mbti_type:
        raise HTTPException(status_code=404, detail="MBTI 类型不存在")

    existing = await session.execute(
        select(Recommendation).where(Recommendation.mbti_type_id == mbti_type.id).limit(1)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="已有推荐，可直接查询，请勿重复生成")

    from app.services.ai_recommender import AIRecommender
    recommender = AIRecommender()
    try:
        books = await recommender.recommend(request.mbti_code, request.count)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"AI 生成失败: {e}")

    saved = []
    # 一次性取出全部书籍，Python 层规范化模糊匹配（数据量小，简单可靠）
    existing_books = (await session.execute(select(Book))).scalars().all()
    for book_data in books:
        target_title = _normalize_book(book_data["title"])
        target_author = _normalize_book(book_data["author"])
        book = next(
            (b for b in existing_books
             if _normalize_book(b.title) == target_title
             and _normalize_book(b.author) == target_author),
            None,
        )

        if not book:
            cover_url = await search_cover(book_data["title"], book_data["author"])
            book = Book(
                title=book_data["title"],
                author=book_data["author"],
                description=book_data["description"],
                genre=book_data["genre"],
                cover_url=cover_url,
            )
            session.add(book)
            await session.flush()
        else:
            # 命中已有书（去重成功）；若该书记录缺封面，顺手补一次查询
            if not book.cover_url:
                cover_url = await search_cover(book_data["title"], book_data["author"])
                if cover_url:
                    book.cover_url = cover_url

        rec = Recommendation(
            mbti_type_id=mbti_type.id,
            book_id=book.id,
            reasoning=book_data["reasoning"],
            relevance_score=8,
            is_ai_generated=True,
        )
        session.add(rec)
        saved.append({
            "book": {"title": book.title, "author": book.author},
            "reasoning": book_data["reasoning"],
        })

    await session.commit()
    return ApiResponse(data=saved, message="AI 推荐生成成功")

@router.get("/mbti/{mbti_code}", response_model=ApiResponse)
async def get_recommendations(mbti_code: str, session: AsyncSession = Depends(get_db)):
    type_result = await session.execute(
        select(MbtiType).where(MbtiType.code == mbti_code.upper())
    )
    mbti_type = type_result.scalar_one_or_none()
    if not mbti_type:
        raise HTTPException(status_code=404, detail="MBTI 类型不存在")

    result = await session.execute(
        select(Recommendation, Book)
        .join(Book, Recommendation.book_id == Book.id)
        .where(Recommendation.mbti_type_id == mbti_type.id)
        .order_by(Recommendation.relevance_score.desc())
    )
    rows = result.all()

    data = []
    for rec, book in rows:
        data.append({
            "id": rec.id,
            "reasoning": rec.reasoning,
            "relevance_score": rec.relevance_score,
            "is_ai_generated": rec.is_ai_generated,
            "likes_count": rec.likes_count,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
            "book": {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "cover_url": book.cover_url,
                "description": book.description,
                "genre": book.genre,
            }
        })

    return ApiResponse(data={
        "items": data,
        "mbti_type": {"code": mbti_type.code, "name": mbti_type.name},
    })
        
