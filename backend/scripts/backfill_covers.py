import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Book
from app.services.douban import search_cover

BATCH = 20 # 每次查询20条数据
DELAY = 2.0 # 每次查询间隔2秒

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Book).where(Book.cover_url.is_(None))
        )
        books = result.scalars().all()
        total = len(books)
        print(f"待回填: {total} 本")
        
        done = 0
        for i, book in enumerate(books, 1):
            url = await search_cover(book.title, book.author)
            if url:
                book.cover_url = url
                done += 1
            if i % BATCH == 0:
                await session.commit()
                print(f"进度: {i}/{total}（已回填 {done}）")
            await asyncio.sleep(DELAY)
            
        await session.commit()
        print(f"完成: 共 {total} 本，回填 {done} 本")
        
if __name__ == "__main__":
    asyncio.run(main())

