# recommendations router
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import MbtiType, Book, Recommendation

from pydantic import BaseModel

class AIGenerateRequest(BaseModel):
    mbti_code: str
    count: int = 5
    
class AIGenerateResponse(BaseModel):
    title: str
    author: str
    description: str
    reasoning: str
    genre: str

router = APIRouter(
    prefix="/api/v1/recommendations",
    tags=["推荐"],
)

@router.post("/ai-generate", status_code=200)
async def ai_generate(
    request: AIGenerateRequest,
    session: AsyncSession = Depends(get_db)
):
    """AI生成推荐"""
    # 验证 MBTI 类型是否存在
    type_result = await session.execute(select(MbtiType).where(MbtiType.code == request.mbti_code.upper()))
    mbti_type = type_result.scalar_one_or_none()
    if not mbti_type:
        raise HTTPException(status_code=404, detail="MBTI 类型不存在")
    
    # 检查是否已有推荐
    existing = await session.execute(select(Recommendation).where(Recommendation.mbti_type_id == mbti_type.id).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="已有推荐，可直接查询，请勿重复生成")
    
    # 调用 AI 推荐接口，生成推荐列表
    from app.services.ai_recommender import AIRecommender
    recommender = AIRecommender()
    books = await recommender.recommend(request.mbti_code, request.count)
    
    # 将推荐结果保存到数据库
    saved = []
    for book_data in books:
        # 检查书籍是否已存在
        book_result = await session.execute(select(Book).where(Book.title == book_data["title"], Book.author == book_data["author"]))
        book = book_result.scalar_one_or_none()
        
        if not book:
            # 如果书籍不存在，则创建新书籍
            book = Book(
                title=book_data["title"],
                author=book_data["author"],
                description=book_data["description"],
                genre=book_data["genre"],
            )
            
            session.add(book)
            await session.flush()
            
        rec = Recommendation(
            mbti_type_id=mbti_type.id,
            book_id=book.id,
            reasoning=book_data["reasoning"],
            relevance_score=8,
            is_ai_generated=True,
        )
        session.add(rec)
        saved.append({
            "book":{"title": book.title, "author": book.author},
            "reasoning": book_data["reasoning"],
        })
        
    await session.commit()

    return {
        "data": saved,
        "source": "ai_generated",
        "cached": False
    }
    

@router.get("/mbti/{mbti_code}")
async def get_recommendations(mbti_code: str, session: AsyncSession = Depends(get_db)):
    """获取指定MBTI类型的推荐书籍"""
    # 先查 MBTI 类型表，获取对应的 MBTI 类型对象
    type_result = await session.execute(select(MbtiType).where(MbtiType.code == mbti_code.upper()))
    mbti_type = type_result.scalar_one_or_none()
    if not mbti_type:
        raise HTTPException(status_code=404, detail="MBTI 类型不存在")

    # 再查推荐表，获取对应的推荐书籍
    result = await session.execute(select(Recommendation, Book).join(Book, Recommendation.book_id == Book.id).where(Recommendation.mbti_type_id == mbti_type.id).order_by(Recommendation.relevance_score.desc()))
    rows = result.all()
    
    data = []
    for rec, book in rows:
        data.append({
            "id": rec.id,
            "reasoning": rec.reasoning,
            "relevance_score": rec.relevance_score,
            "is_ai_generated": rec.is_ai_generated,
            "likes_count": rec.likes_count,
            "created_at": rec.created_at,
            "book": {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "cover_url": book.cover_url,
                "description": book.description,
                "genre": book.genre,
            }
        })
    
    return {
        "data": data,
        "mbti_type": {"code": mbti_type.code, "name": mbti_type.name}
    }
        
