# 数据库迁移：创建社交功能两张表
#   book_ratings（用户对书籍的 1-5 星评分，UNIQUE(user_id, book_id)）
#   user_follows（用户关注关系，UNIQUE(follower_id, following_id)）
# 并确保 users 表存在 is_profile_public 列（公开主页开关，幂等 ALTER）。
# 用法（backend 目录）：uv run python scripts/create_social_tables.py
# 幂等：已存在的表自动跳过（create_all 只创建缺失表）。
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import async_engine
from app.models import Base  # noqa: F401  # 导入全部模型注册到 metadata
import app.models.book_rating  # noqa: F401
import app.models.user_follow  # noqa: F401
import app.models.user  # noqa: F401  # users 表加列需要模型注册


async def main():
    # create_all 建缺失表（含新表的唯一约束/索引/外键）
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # users 表补 is_profile_public 列（create_all 不会给已存在的表加列，需幂等 ALTER）
    async with async_engine.begin() as conn:
        has_col = (await conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'users' AND column_name = 'is_profile_public'"
        ))).scalar()
        if not has_col:
            await conn.execute(text(
                "ALTER TABLE users ADD COLUMN is_profile_public TINYINT(1) NOT NULL DEFAULT 1"
            ))
            print("users.is_profile_public 列已添加（默认公开）")
        else:
            print("[跳过] users.is_profile_public 列已存在")

    # 列出两张新表结构，确认建表成功
    async with async_engine.begin() as conn:
        for table in ("book_ratings", "user_follows"):
            rows = (await conn.execute(text(
                f"SHOW CREATE TABLE {table}"
            ))).all()
            print(f"{table} 表创建/已存在，结构确认：")
            print(rows[0][1][:600] if rows else f"未找到 {table} 表")


if __name__ == "__main__":
    asyncio.run(main())
