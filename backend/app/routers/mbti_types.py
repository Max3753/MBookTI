# MBTI_TYPE ROUTER
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MbtiType

router = APIRouter(
    prefix="/api/v1/mbti_types",
    tags=["MBTI 类型"]
)

@router.get("")
async def list_mbti_types(session: AsyncSession = Depends(get_db)):
    """获取所有 MBTI 类型"""
    result = await session.execute(select(MbtiType).order_by(MbtiType.id))
    types = result.scalars().all()
    return {"data": types, "total": len(types)}

@router.get("/{code}")
async def get_mbti_type(code: str, session: AsyncSession = Depends(get_db)):
    """获取指定 MBTI 详细类型"""
    result = await session.execute(select(MbtiType).where(MbtiType.code == code.upper()))
    mbti_type = result.scalar_one_or_none()
    if not mbti_type:
        raise HTTPException(status_code=404, detail="MBTI 类型不存在")
    return {"data": mbti_type}

