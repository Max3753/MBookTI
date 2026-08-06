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
#   - 未命中     → 从数据库已有书籍中按人格偏好换一批未推荐过的（零 AI 费用、零新增书籍）
# 首次生成（无旧推荐）不受此概率影响，必定调用 AI。
# 概率取黄金比例 0.618：AI 分支略占优，兼顾内容质量与成本。
AI_REGENERATE_PROBABILITY = 0.618


def _normalize_book(s: str) -> str:
    """书籍查重用规范化：去掉书名号/空格/连字符/标点等。

    AI 生成的 title/author 常带细微差异（《》、-、· 等），
    精确匹配必然查不到已有书籍导致重复入库，故统一归一化后比较。
    """
    import re
    return re.sub(r"[\s《》·\-—:：,，.。\"'“”]+", "", s or "")


async def _delete_existing_recommendations(session: AsyncSession, mbti_type_id: int) -> list[int]:
    """删除某 MBTI 类型已有的推荐记录，返回被删除推荐所关联的书籍 id 列表。

    只删除 recommendations 关系，不碰书籍/评论/收藏；
    评论对该类型旧推荐的外键引用先置空，评论本身保留。
    返回的 book_id 列表用于「换书分支」排除，避免换到刚展示过的书。
    """
    old_recs = (
        await session.execute(
            select(Recommendation).where(Recommendation.mbti_type_id == mbti_type_id)
        )
    ).scalars().all()
    if not old_recs:
        return []
    old_book_ids = [r.book_id for r in old_recs]
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
    return old_book_ids


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
    mbti_code: str,
    exclude_book_ids: list[int] | None = None,
) -> list[dict]:
    """从数据库已有书籍中换一批「该类型未推荐过」的书，并体现 MBTI 人格关联。

    零 AI 费用、零新增书籍；只替换推荐关系。
    关联性策略：优先挑选该类型偏好体裁（MBTI_PROFILES[code].genres）的书，
    不足时再随机补足；reasoning 文案结合类型特质与书籍简介生成。
    exclude_book_ids：刚被删除的旧推荐书籍 id，换书时排除，避免换到刚展示过的书。
    """
    from app.services.ai_recommender import MBTI_PROFILES

    profile = MBTI_PROFILES.get(mbti_code.upper(), {})
    preferred_genres = set(profile.get("genres") or [])
    traits = profile.get("traits") or []
    trait_hint = traits[0] if traits else "该类型"

    # 已推荐给该类型的书籍 id（避免重复展示）
    recommended_book_ids = (
        await session.execute(
            select(Recommendation.book_id).where(Recommendation.mbti_type_id == mbti_type_id)
        )
    ).scalars().all()

    # 合并排除：当前已推荐的 + 刚删除的旧推荐（防止换回刚看过的）
    exclude = set(recommended_book_ids) | set(exclude_book_ids or [])

    def _query(genre_filter: bool):
        query = select(Book)
        if exclude:
            query = query.where(Book.id.not_in(list(exclude)))
        if genre_filter:
            query = query.where(Book.genre.in_(list(preferred_genres)))
        return query

    # 第一优先：该类型偏好体裁的书
    preferred_books = (await session.execute(_query(True))).scalars().all()
    # 第二优先：其余书（补足数量）
    fallback_books = (await session.execute(_query(False))).scalars().all()

    import random
    picked = []
    if preferred_books:
        picked = random.sample(preferred_books, k=min(count, len(preferred_books)))
    if len(picked) < count:
        # 补足时排除已选中的，避免重复
        picked_ids = {b.id for b in picked}
        rest = [b for b in fallback_books if b.id not in picked_ids]
        picked += random.sample(rest, k=min(count - len(picked), len(rest)))

    def _reasoning(book: Book) -> str:
        """按是否命中偏好体裁生成带人格关联的推荐文案。"""
        desc = (book.description or "").strip()
        snippet = desc[:40] + ("…" if len(desc) > 40 else "")
        if book.genre in preferred_genres:
            base = f"这本书属于「{book.genre}」类，正中 {mbti_code} 对「{trait_hint}」的偏好。"
        else:
            base = f"为你精选的{book.genre or '好书'}，值得一读。"
        return f"{base}{snippet}" if snippet else base

    saved = []
    for book in picked:
        rec = Recommendation(
            mbti_type_id=mbti_type_id,
            book_id=book.id,
            reasoning=_reasoning(book),
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
        old_book_ids = await _delete_existing_recommendations(session, mbti_type.id)
        saved = await _rotate_from_library(
            session, request.count, mbti_type.id, request.mbti_code, exclude_book_ids=old_book_ids
        )
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

    # 一次性批量聚合这批书的用户评分（平均分保留 1 位小数，无评分返回 None）
    from sqlalchemy import func as sa_func
    from app.models import BookRating
    book_ids = [book.id for _, book in rows]
    rating_map: dict[int, tuple] = {}
    if book_ids:
        agg_rows = (await session.execute(
            select(
                BookRating.book_id,
                sa_func.avg(BookRating.rating),
                sa_func.count(BookRating.id),
            )
            .where(BookRating.book_id.in_(book_ids))
            .group_by(BookRating.book_id)
        )).all()
        rating_map = {
            bid: (round(float(avg), 1) if avg is not None else None, cnt or 0)
            for bid, avg, cnt in agg_rows
        }

    data = []
    for rec, book in rows:
        avg_rating, rating_count = rating_map.get(book.id, (None, 0))
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
                "avg_rating": avg_rating,
                "rating_count": rating_count,
            }
        })

    return ApiResponse(data={
        "items": data,
        "mbti_type": {"code": mbti_type.code, "name": mbti_type.name},
    })
        
