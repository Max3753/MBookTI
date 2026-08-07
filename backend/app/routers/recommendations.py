from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MbtiType, Book, Recommendation, User, Comment
from app.schemas import ApiResponse, AIGenerateRequest
from app.auth.deps import get_current_user
from app.services.douban import search_cover

import json
import logging
import random

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/recommendations",
    tags=["推荐"],
)

# 每次点击「AI 生成」后，书单中**每一本书独立决定来源**：
#   - 命中该概率 → AI 生成一本「数据库中不存在」的新书（入库）
#   - 未命中     → 从数据库已有书籍中挑一本（复用已有对象，零新增）
# 逐本独立 → 每次生成的书单是「AI 新书 + 库内已有书」的混合体，集合不再整批重复。
# 首次生成（库中无书）不受此概率影响，必定全部走 AI。
# 概率取黄金比例 0.618：AI 来源略占优，兼顾内容质量与成本。
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


async def _upsert_book(session: AsyncSession, book_data: dict, existing_books: list[Book]) -> tuple[Book, bool]:
    """根据 AI 返回的书籍数据查重 / 新建 / 补封面，返回 (Book, created)。

    created=True 表示本次新建入库（数据库中不存在的**新书籍对象**）；
    created=False 表示命中已有书（复用既有对象，不重复入库）。
    existing_books：一次性取出的全库书籍（Python 层规范化模糊匹配，数据量小，简单可靠）。
    新建的书会追加进 existing_books，保证同一批内 AI 重复输出同本书时命中同一条记录（不重复入库）。
    """
    target_title = _normalize_book(book_data["title"])
    target_author = _normalize_book(book_data["author"])
    book = next(
        (b for b in existing_books
         if _normalize_book(b.title) == target_title
         and _normalize_book(b.author) == target_author),
        None,
    )
    if book:
        # 命中已有书（去重成功）；若该书记录缺封面，顺手补一次查询
        if not book.cover_url:
            cover_url = await search_cover(book_data["title"], book_data["author"])
            if cover_url:
                book.cover_url = cover_url
        return book, False

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
    existing_books.append(book)
    return book, True


async def _ai_generate_candidates(
    mbti_code: str,
    count: int,
    exclude_titles: list[str],
) -> list[dict]:
    """调用 AI 生成 count 本「库中没有」的新书候选（只含书籍数据，不带推荐词）。

    exclude_titles：库中已有书名（含刚展示过的），prompt 要求 AI 源头避开。
    推荐词由调用方在书单确认后统一生成（见 _ai_generate_reasonings）。
    只返回原始候选数据，不查重、不入库；AI 调用失败抛 RuntimeError，由调用方降级。
    """
    from app.services.ai_recommender import AIRecommender
    recommender = AIRecommender()
    return await recommender.recommend(
        mbti_code, count, exclude_titles=exclude_titles, with_reasoning=False
    )


async def _ai_generate_reasonings(
    mbti_code: str,
    books: list[Book],
) -> dict[int, str]:
    """为书单中的全部书批量生成三要素推荐文案（一次独立 AI 调用）。

    书单确认后调用：AI 新书与库内书统一生成，文案风格一致、不可分辨来源。
    任何失败返回空 dict，由调用方降级为模板文案（不阻断生成流程）。
    """
    if not books:
        return {}
    lines = "\n".join(
        f"{i + 1}. 《{b.title}》{b.author}（类别：{b.genre or '未知'}；"
        f"简介：{(b.description or '').strip()[:80]}）"
        for i, b in enumerate(books)
    )
    prompt = f"""
你是一位专业的阅读顾问。用户的MBTI类型是 {mbti_code}。

以下是本次要推荐给该用户的书（书名/作者/类别/简介）：
{lines}

要求：
1. 为每本书生成一条推荐理由，必须包含三要素：① 这本书讲什么（点名核心内容/主题）② 读了能获得什么（收益钩子）③ 与 {mbti_code} 特质的关联（为什么适合这个人格）
2. 每条约 100-180 字，语气自然流畅，不要模板化套话
3. 输出必须是**严格合法的单个 JSON 对象**，不要 markdown 代码块，不要任何前后缀文字或注释：
{{"reasonings": ["第1本的推荐理由", "第2本的推荐理由", ...]}}
- 所有字符串必须用半角双引号包裹，字符串内禁止出现换行符
"""
    from app.services.ai_recommender import AIRecommender
    recommender = AIRecommender()
    # 推荐词生成重试（最多 3 次）：一次性网络抖动/格式错误不再直接降级模板，
    # 模板文案只做最后兜底。与候选生成共用客户端的 timeout/max_retries 配置。
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = await recommender.client.chat.completions.create(
                model=recommender.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=4096,  # 防 count 较大时输出截断 → JSON 不完整 → 无谓重试
            )
        except Exception as e:
            last_error = e
            continue  # 网络/服务错误：重试

        # token 用量日志：便于统计每次生成的成本
        usage = getattr(response, "usage", None)
        if usage is not None:
            logger.info(
                "AI 推荐词生成完成 mbti=%s books=%d attempt=%d prompt_tokens=%s completion_tokens=%s total=%s",
                mbti_code, len(books), attempt,
                getattr(usage, "prompt_tokens", "?"),
                getattr(usage, "completion_tokens", "?"),
                getattr(usage, "total_tokens", "?"),
            )

        raw = AIRecommender._extract_json(response.choices[0].message.content or "")
        if not raw:
            last_error = RuntimeError("AI 推荐词返回内容中没有 JSON")
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            last_error = RuntimeError(f"AI 推荐词 JSON 解析失败: {e}")
            continue
        reasonings = data.get("reasonings") or []
        result = {
            b.id: r
            for b, r in zip(books, reasonings)
            if isinstance(r, str) and r.strip()
        }
        if result:
            return result
        last_error = RuntimeError("AI 推荐词列表为空或字段不完整")

    # 全部重试失败：记录日志，由调用方降级为模板文案（不阻断生成流程）
    logger.warning(
        "AI 推荐词生成失败，降级模板文案 mbti=%s books=%d err=%s",
        mbti_code, len(books), last_error,
    )
    return {}


def _template_reasoning(mbti_code: str, book: Book, preferred_genres: set[str], trait_hint: str) -> str:
    """模板推荐文案：AI 文案生成失败时的降级兜底（按是否命中偏好体裁生成）。"""
    desc = (book.description or "").strip()
    snippet = desc[:40] + ("…" if len(desc) > 40 else "")
    if book.genre in preferred_genres:
        base = f"这本书属于「{book.genre}」类，正中 {mbti_code} 对「{trait_hint}」的偏好。"
    else:
        base = f"为你精选的{book.genre or '好书'}，值得一读。"
    return f"{base}{snippet}" if snippet else base


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

    picked = []
    if preferred_books:
        picked = random.sample(preferred_books, k=min(count, len(preferred_books)))
    if len(picked) < count:
        # 补足时排除已选中的，避免重复
        picked_ids = {b.id for b in picked}
        rest = [b for b in fallback_books if b.id not in picked_ids]
        picked += random.sample(rest, k=min(count - len(picked), len(rest)))

    saved = []
    for book in picked:
        rec = Recommendation(
            mbti_type_id=mbti_type_id,
            book_id=book.id,
            reasoning=_template_reasoning(mbti_code, book, preferred_genres, trait_hint),
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

    # 1. 删除该类型旧推荐，拿到刚展示过的书籍 id（本次生成时排除，保证书单互相独立）
    old_book_ids = await _delete_existing_recommendations(session, mbti_type.id)

    # 2. 一次性取出全库书籍：既是 AI 查重基准，也是「库内已有」来源池
    existing_books = (await session.execute(select(Book))).scalars().all()
    library_pool = [b for b in existing_books if b.id not in set(old_book_ids)]

    # 3. 一次 AI 调用生成 count 本「库中没有」的新书候选（prompt 排除库中已有书名）
    try:
        ai_candidates = await _ai_generate_candidates(
            request.mbti_code,
            request.count,
            exclude_titles=[b.title for b in existing_books],
        )
    except RuntimeError as e:
        # AI 服务不可用 → 整批降级为库内换书（零 AI 费用兜底）。
        # 结构化日志便于事后追溯：哪次生成、什么类型、因何降级。
        logger.warning(
            "AI 推荐生成降级为库内换书 mbti_code=%s count=%d err=%s",
            request.mbti_code, request.count, e,
        )
        saved = await _rotate_from_library(
            session, request.count, mbti_type.id, request.mbti_code, exclude_book_ids=old_book_ids
        )
        if not saved:
            raise HTTPException(status_code=500, detail=f"AI 生成失败且书库无书可换: {e}")
        await session.commit()
        # degraded=True：供前端感知「本次书单全部来自书库」（评分全 5 分的来源）
        return ApiResponse(data=saved, message="AI 服务暂不可用，已从书库为你挑选推荐", degraded=True)

    # 4. 逐本独立决定来源：61.8% 取 AI 新书候选，38.2% 从库内已有池随机挑
    saved = []          # 内部条目：{"book": Book 对象, "is_ai": bool}
    used_book_ids = set(old_book_ids)
    ai_iter = iter(ai_candidates)

    for _ in range(request.count):
        book_data = None

        # 位次 A：AI 新书来源（61.8%）
        if random.random() < AI_REGENERATE_PROBABILITY:
            book_data = next(ai_iter, None)
            if book_data is not None:
                book, created = await _upsert_book(session, book_data, existing_books)
                if book.id in used_book_ids:
                    book = None  # AI 违背排除要求给出重复书 → 放弃该候选，回退库内
                else:
                    # created=True：AI 生成的新对象；created=False：命中库中已有（归库内来源）
                    used_book_ids.add(book.id)
                    saved.append({"book": book, "is_ai": created})
                    continue

        # 位次 B：库内已有来源（38.2% / AI 候选不可用时的回退）
        pool = [b for b in library_pool if b.id not in used_book_ids]
        if pool:
            book = random.choice(pool)
            used_book_ids.add(book.id)
            saved.append({"book": book, "is_ai": False})
            continue

        # 位次 C：库内耗尽 → 用剩余 AI 候选补足（候选也耗尽则书单变短）
        if book_data is None:
            book_data = next(ai_iter, None)
        if book_data is not None:
            book, created = await _upsert_book(session, book_data, existing_books)
            if book.id not in used_book_ids:
                used_book_ids.add(book.id)
                saved.append({"book": book, "is_ai": created})

    # 5. 书单确认后，所有书（AI 新书 + 库内书）的推荐词一次独立调用统一生成
    if saved:
        reasoning_map = await _ai_generate_reasonings(
            request.mbti_code, [item["book"] for item in saved]
        )
        from app.services.ai_recommender import MBTI_PROFILES
        profile = MBTI_PROFILES.get(request.mbti_code.upper(), {})
        preferred_genres = set(profile.get("genres") or [])
        trait_hint = (profile.get("traits") or [""])[0] or "该类型"
        for item in saved:
            item["reasoning"] = reasoning_map.get(item["book"].id)
            if not item["reasoning"]:
                # AI 文案生成失败/缺失：退回模板文案，保证书单完整
                item["reasoning"] = _template_reasoning(
                    request.mbti_code, item["book"], preferred_genres, trait_hint
                )

    # 6. 入库推荐关系（每本书一条 Recommendation，供展示/评论/点赞引用）
    for item in saved:
        rec = Recommendation(
            mbti_type_id=mbti_type.id,
            book_id=item["book"].id,
            reasoning=item["reasoning"],
            relevance_score=8 if item["is_ai"] else 5,
            is_ai_generated=item["is_ai"],
        )
        session.add(rec)

    # 响应：只暴露 book(title/author) + reasoning
    data = [
        {
            "book": {"title": item["book"].title, "author": item["book"].author},
            "reasoning": item["reasoning"],
        }
        for item in saved
    ]

    await session.commit()
    return ApiResponse(data=data, message="AI 推荐生成成功")

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
        
