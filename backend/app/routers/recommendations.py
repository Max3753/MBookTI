from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MbtiType, Book, Recommendation, User, Comment
from app.schemas import ApiResponse, AIGenerateRequest
from app.auth.deps import get_current_user
from app.services.douban import search_cover

router = APIRouter(
    prefix="/api/v1/recommendations",
    tags=["推荐"],
)

# 已有推荐时再次点击「AI 生成」，随机决定走哪条分支：
#   - 命中该概率 → 重新调用 AI 生成全新推荐
#   - 未命中     → 从数据库已有书籍中随机换一批未推荐过的（零 AI 费用、零新增书籍）
# 首次生成（无旧推荐）不受此概率影响，必定调用 AI。
AI_REGENERATE_PROBABILITY = 0.5


def _normalize_book(s: str) -> str:
    """书籍查重用规范化：去掉书名号/空格/连字符/标点等。

    AI 生成的 title/author 常带细微差异（《》、-、· 等），
    精确匹配必然查不到已有书籍导致重复入库，故统一归一化后比较。
    """
    import re
    return re.sub(r"[\s《》·\-—:：,，.。\"'“”]+", "", s or "")


async def _delete_existing_recommendations(session: AsyncSession, mbti_type_id: int) -> None:
    """删除某 MBTI 类型已有的推荐记录。

    只删除 recommendations 关系，不碰书籍/评论/收藏；
    评论对该类型旧推荐的外键引用先置空，评论本身保留。
    """
    old_recs = (
        await session.execute(
            select(Recommendation).where(Recommendation.mbti_type_id == mbti_type_id)
        )
    ).scalars().all()
    if not old_recs:
        return
    rec_ids = [r.id for r in old_recs]
    await session.execute(
        update(Comment)
        .where(Comment.recommendation_id.in_(rec_ids))
        .values(recommendation_id=None)
    )
    await session.execute(
        delete(Recommendation).where(Recommendation.id.in_(rec_ids))
    )
    await session.flush()


async def _generate_with_ai(
    session: AsyncSession,
    mbti_code: str,
    count: int,
    mbti_type_id: int,
) -> list[dict]:
    """调用 DeepSeek 生成推荐：已有书复用（去重），新书入库。"""
    from app.services.ai_recommender import AIRecommender
    recommender = AIRecommender()
    try:
        books = await recommender.recommend(mbti_code, count)
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
            mbti_type_id=mbti_type_id,
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
    return saved


async def _rotate_from_library(
    session: AsyncSession,
    count: int,
    mbti_type_id: int,
) -> list[dict]:
    """从数据库已有书籍中随机换一批「该类型未推荐过」的书。

    零 AI 费用、零新增书籍；只替换推荐关系。
    """
    # 已推荐给该类型的书籍 id（避免重复展示）
    recommended_book_ids = (
        await session.execute(
            select(Recommendation.book_id).where(Recommendation.mbti_type_id == mbti_type_id)
        )
    ).scalars().all()

    query = select(Book)
    if recommended_book_ids:
        query = query.where(Book.id.not_in(recommended_book_ids))
    all_books = (await session.execute(query)).scalars().all()

    import random
    picked = random.sample(all_books, k=min(count, len(all_books))) if all_books else []

    saved = []
    for book in picked:
        rec = Recommendation(
            mbti_type_id=mbti_type_id,
            book_id=book.id,
            reasoning=f"为你随机挑选的 {book.genre or '好书'}，换换口味。",
            relevance_score=5,
            is_ai_generated=False,
        )
        session.add(rec)
        saved.append({
            "book": {"title": book.title, "author": book.author},
            "reasoning": rec.reasoning,
        })
    return saved


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
    has_existing = existing.scalar_one_or_none() is not None

    # 已有推荐时掷硬币决定分支；首次生成必定调 AI
    use_ai = (not has_existing)
    if has_existing:
        import random
        use_ai = random.random() < AI_REGENERATE_PROBABILITY

    if use_ai:
        await _delete_existing_recommendations(session, mbti_type.id)
        saved = await _generate_with_ai(session, request.mbti_code, request.count, mbti_type.id)
        message = "AI 推荐重新生成成功" if has_existing else "AI 推荐生成成功"
    else:
        await _delete_existing_recommendations(session, mbti_type.id)
        saved = await _rotate_from_library(session, request.count, mbti_type.id)
        # 兜底：库里可选书不足时，随机换书可能为空/偏少，转 AI 补足
        if len(saved) < request.count:
            await _delete_existing_recommendations(session, mbti_type.id)
            saved = await _generate_with_ai(session, request.mbti_code, request.count, mbti_type.id)
            message = "AI 推荐重新生成成功（库内书籍不足，已转 AI 补充）"
        else:
            message = "已为你从书库中随机换了一批推荐"

    await session.commit()
    return ApiResponse(data=saved, message=message)

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
        
