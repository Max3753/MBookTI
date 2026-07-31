# 数据库加固迁移：users.password_changed_at 改为 DATETIME(6)（微秒精度）
# 背景：改密/重置后旧 token 失效依赖 issued_at < password_changed_at 比较。
#       原列 DATETIME 为秒精度，若登录与改密发生在同一秒，issued_at == changed_at，
#       比较不成立导致旧 token 在 1 秒窗口内仍有效。DATETIME(6) 保留微秒，
#       使改密时刻（微秒）恒大于同秒签发的 iat（秒），旧 token 必然失效。
# 用法（backend 目录）：.venv\Scripts\python.exe scripts\upgrade_password_changed_at_precision.py
# 幂等：列类型已是 datetime(6) 时跳过
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as s:
        cols = (await s.execute(text("SHOW COLUMNS FROM users"))).all()
        col = next((r for r in cols if r[0] == "password_changed_at"), None)
        if col is None:
            print("[跳过] users.password_changed_at 不存在")
            return
        col_type = str(col[1]).lower()
        if "datetime(6)" in col_type:
            print("[跳过] users.password_changed_at 已是 DATETIME(6)")
            return

        await s.execute(text("ALTER TABLE users MODIFY password_changed_at DATETIME(6) NULL"))
        await s.commit()
        print("已迁移：users.password_changed_at -> DATETIME(6)（微秒精度）")


if __name__ == "__main__":
    asyncio.run(main())
