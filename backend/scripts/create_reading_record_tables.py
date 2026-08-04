# 数据库迁移：创建阅读进度同步表 reading_records
# 用法（backend 目录）：uv run python scripts/create_reading_record_tables.py
# 幂等：已存在的表自动跳过（create_all 只创建缺失表）。
# 同时清理废弃的 user_books 表（云端文件书库已取消，改为本地文件 + 云端进度）。
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import async_engine
from app.models import Base  # noqa: F401  # 导入全部模型注册到 metadata
import app.models.reading_record  # noqa: F401


async def main():
    # create_all 建缺失表（含新表的索引/唯一约束/外键）
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 清理已废弃的 user_books 表（云端文件书库取消；仅开发期测试数据，无生产数据）
    async with async_engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS user_books"))

    # 列出 reading_records 表结构，确认建表成功
    async with async_engine.begin() as conn:
        rows = (await conn.execute(text(
            "SHOW CREATE TABLE reading_records"
        ))).all()
    print("reading_records 表创建/已存在，结构确认：")
    print(rows[0][1][:600] if rows else "未找到 reading_records 表")


if __name__ == "__main__":
    asyncio.run(main())
