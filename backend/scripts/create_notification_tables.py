# 数据库迁移：创建通知系统三张表
#   announcements（系统公告本体）
#   announcement_acks（公告确认状态，UNIQUE(announcement_id, user_id)）
#   notifications（个人通知：评论获赞 / 管理员消息）
# 用法（backend 目录）：uv run python scripts/create_notification_tables.py
# 幂等：已存在的表自动跳过（create_all 只创建缺失表）
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import AsyncSessionLocal, async_engine
from app.models import Base  # noqa: F401  # 导入全部模型注册到 metadata
import app.models.announcement  # noqa: F401
import app.models.notification  # noqa: F401


async def main():
    # create_all 建缺失表（含新表的 UNIQUE 约束）
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 补充检查：ack 表加 UNIQUE 约束（create_all 已含，这里幂等兜底）
    async with AsyncSessionLocal() as s:
        idx = (await s.execute(text("SHOW INDEX FROM announcement_acks"))).all()
        if not any(r[2] == "uq_announcement_ack" for r in idx):
            await s.execute(text(
                "ALTER TABLE announcement_acks "
                "ADD CONSTRAINT uq_announcement_ack UNIQUE (announcement_id, user_id)"
            ))
            await s.commit()
            print("已添加 UNIQUE(announcement_id, user_id)")
        else:
            print("[跳过] UNIQUE 约束已存在")

    # 列出当前通知相关表
    rows = (await s.execute(text(
        "SHOW TABLES LIKE 'announcement%'"
    ))).all()
    nrows = (await s.execute(text("SHOW TABLES LIKE 'notification%'"))).all()
    print("通知相关表:", [r[0] for r in rows] + [r[0] for r in nrows])


if __name__ == "__main__":
    asyncio.run(main())
