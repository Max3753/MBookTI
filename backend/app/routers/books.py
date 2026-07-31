from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Book
from app.schemas import ApiResponse, BookResponse

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
