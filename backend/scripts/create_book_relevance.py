# 数据库迁移：创建 book_relevance 表
#   book_relevance（书籍 × MBTI 类型的 AI 相关度评分缓存，UNIQUE(book_id, mbti_type_id)）
# 用法（backend 目录）：uv run python scripts/create_book_relevance.py
# 幂等：已存在的表自动跳过（create_all 只创建缺失表）。
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import async_engine
from app.models import Base  # noqa: F401  # 导入全部模型注册到 metadata
import app.models.book_relevance  # noqa: F401


async def main():
    # create_all 建缺失表（含唯一约束/索引/外键）
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 列出新表结构，确认建表成功
    async with async_engine.begin() as conn:
        rows = (await conn.execute(text(
            "SHOW CREATE TABLE book_relevance"
        ))).all()
        print("book_relevance 表创建/已存在，结构确认：")
        print(rows[0][1][:600] if rows else "未找到 book_relevance 表")


if __name__ == "__main__":
    asyncio.run(main())
