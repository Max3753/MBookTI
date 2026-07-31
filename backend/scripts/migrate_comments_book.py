# 数据库迁移：comments 表加 book_id（书评挂到书，跨 MBTI 类型聚合）
# 用法（backend 目录）：uv run python scripts/migrate_comments_book.py
# 幂等：已存在 book_id 列时直接跳过
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as s:
        # 0. 检查是否已迁移
        cols = (await s.execute(text("SHOW COLUMNS FROM comments"))).all()
        if any(r[0] == "book_id" for r in cols):
            print("[跳过] comments.book_id 已存在，无需迁移")
            return

        # 1. 备份
        await s.execute(text("CREATE TABLE IF NOT EXISTS comments_backup AS SELECT * FROM comments"))
        print("[1/5] 已备份 comments -> comments_backup")

        # 2. 加列（先允许 NULL）
        await s.execute(text("ALTER TABLE comments ADD COLUMN book_id INT NULL AFTER recommendation_id"))
        print("[2/5] 已添加 book_id 列")

        # 3. 回填：从 recommendations 反查书
        await s.execute(text(
            "UPDATE comments c JOIN recommendations r ON c.recommendation_id = r.id SET c.book_id = r.book_id"
        ))
        print("[3/5] 已回填 book_id（按推荐记录反查）")

        # 4. 校验：不应有悬空评论
        orphan = (await s.execute(text("SELECT COUNT(*) FROM comments WHERE book_id IS NULL"))).scalar()
        if orphan:
            print(f"[警告] {orphan} 条评论未映射到书（recommendation_id 悬空），请检查后再执行 NOT NULL")
            await s.rollback()
            return

        # 5. NOT NULL + 外键
        await s.execute(text("ALTER TABLE comments MODIFY COLUMN book_id INT NOT NULL"))
        await s.execute(text("ALTER TABLE comments ADD CONSTRAINT fk_comments_book FOREIGN KEY (book_id) REFERENCES books(id)"))
        print("[5/5] book_id 已设为 NOT NULL 并加外键")

        await s.commit()
        print("迁移完成 ✓")


if __name__ == "__main__":
    asyncio.run(main())
