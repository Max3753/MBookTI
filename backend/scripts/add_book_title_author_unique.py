# 数据库迁移：books 表加 (title, author) 联合唯一约束
#   背景：isbn 由 AI 生成，从未写入（100% 为 NULL），isbn 唯一约束空转，
#         导致同名同作者的重复书籍可以无限入库。本脚本以 (title, author)
#         作为真实去重键，先在数据库层清理既有重复（保留最小 id，重定向
#         外键引用），再添加联合唯一约束。
# 用法（backend 目录）：uv run python scripts/add_book_title_author_unique.py
# 幂等：约束已存在时自动跳过；无重复数据时直接加约束。
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import async_engine

# 引用 books.id 的表（清理重复时需把被删记录的 book_id 重定向到保留记录）
BOOK_REF_TABLES = [
    "book_ratings",
    "comments",
    "book_relevance",
    "recommendations",
    "user_book_favorites",
]

CONSTRAINT_NAME = "uq_books_title_author"


async def table_exists(conn, name: str) -> bool:
    row = (await conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = :n"
    ), {"n": name})).scalar()
    return bool(row)


async def constraint_exists(conn) -> bool:
    row = (await conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.table_constraints "
        "WHERE table_schema = DATABASE() AND table_name = 'books' "
        "AND constraint_name = :n"
    ), {"n": CONSTRAINT_NAME})).scalar()
    return bool(row)


async def main():
    async with async_engine.begin() as conn:
        if not await table_exists(conn, "books"):
            print("books 表不存在，跳过")
            return

        if await constraint_exists(conn):
            print(f"约束 {CONSTRAINT_NAME} 已存在，跳过")
            return

        # 1. 找出 (title, author) 精确重复组（保留最小 id）
        dups = (await conn.execute(text("""
            SELECT title, author, MIN(id) AS keep_id, COUNT(*) AS cnt
            FROM books
            GROUP BY title, author
            HAVING COUNT(*) > 1
        """))).all()

        if dups:
            print(f"发现 {len(dups)} 组重复，开始合并（保留最小 id）...")
            for d in dups:
                keep_id = d.keep_id
                dup_ids = (await conn.execute(text(
                    "SELECT id FROM books WHERE title = :t AND author = :a AND id != :keep"
                ), {"t": d.title, "a": d.author, "keep": keep_id})).scalars().all()
                id_list = ",".join(str(i) for i in dup_ids)
                print(f"  合并: {d.title[:40]} | {d.author[:20]} (x{d.cnt}) -> 保留 id={keep_id}, 删除 {id_list}")

                # 2. 外键引用重定向到保留 id
                for tbl in BOOK_REF_TABLES:
                    if not await table_exists(conn, tbl):
                        continue
                    await conn.execute(text(
                        f"UPDATE {tbl} SET book_id = :keep WHERE book_id IN ({id_list})"
                    ), {"keep": keep_id})

                # 3. 删除重复记录
                await conn.execute(text(
                    f"DELETE FROM books WHERE id IN ({id_list})"
                ))
            print("重复合并完成")
        else:
            print("无 (title, author) 精确重复，直接加约束")

        # 4. 添加联合唯一约束
        await conn.execute(text(
            f"ALTER TABLE books ADD CONSTRAINT {CONSTRAINT_NAME} UNIQUE (title, author)"
        ))
        print(f"约束 {CONSTRAINT_NAME} 添加成功")

    # 确认
    async with async_engine.begin() as conn:
        rows = (await conn.execute(text(
            "SHOW CREATE TABLE books"
        ))).all()
        print("\nbooks 表结构（含约束）：")
        print(rows[0][1][:800] if rows else "未找到 books 表")


if __name__ == "__main__":
    asyncio.run(main())
