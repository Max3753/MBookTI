# 数据库修复：comments.recommendation_id 改允许 NULL
# 背景：书评重构后 recommendation_id 仅兼容旧数据（可空），但 MySQL 表结构仍为 NOT NULL，
#       导致新评论（recommendation_id=NULL）触发 IntegrityError(1048) → 500。
# 用法（backend 目录）：uv run python scripts/fix_comments_recommendation_nullable.py
# 幂等：recommendation_id 已是 NULL 时跳过
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as s:
        cols = (await s.execute(text("SHOW COLUMNS FROM comments"))).all()
        rec_col = next((r for r in cols if r[0] == "recommendation_id"), None)
        if rec_col is None:
            print("[错误] 未找到 recommendation_id 列")
            return
        if rec_col[2] == "YES":  # Null 列位置（第3个字段）
            print("[跳过] recommendation_id 已允许 NULL")
            return

        await s.execute(text("ALTER TABLE comments MODIFY COLUMN recommendation_id INT NULL"))
        await s.commit()
        print("已修复：comments.recommendation_id 改为 NULL（可空）")


if __name__ == "__main__":
    asyncio.run(main())
