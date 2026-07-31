# 数据库加固迁移：users 表新增 password_changed_at 列
# 背景：改密码后旧的 JWT（自包含、不查库）在其过期前仍有效，是安全缺口。
#       该列非空时，auth 层要求 token 签发时间(iat) >= password_changed_at，否则 401，
#       使改密后旧 token 立即失效。已有用户为 NULL（不检查），保持兼容。
# 用法（backend 目录）：uv run python scripts/add_password_changed_at.py
# 幂等：列已存在时跳过
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as s:
        cols = (await s.execute(text("SHOW COLUMNS FROM users"))).all()
        if any(r[0] == "password_changed_at" for r in cols):
            print("[跳过] users.password_changed_at 已存在")
            return

        await s.execute(text("ALTER TABLE users ADD COLUMN password_changed_at DATETIME NULL"))
        await s.commit()
        print("已迁移：users.password_changed_at 新增（NULL）")


if __name__ == "__main__":
    asyncio.run(main())
