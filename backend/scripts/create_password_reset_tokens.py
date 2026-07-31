# 数据库迁移：创建 password_reset_tokens 表（忘记密码一次性重置令牌）
# 结构：id INT PK AUTO_INCREMENT / user_id INT NOT NULL FK users.id /
#       token_hash CHAR(64) UNIQUE NOT NULL（sha256 hex）/ expires_at DATETIME NOT NULL /
#       used_at DATETIME NULL / created_at DATETIME DEFAULT NOW()
# 用法（backend 目录）：.venv\Scripts\python.exe scripts\create_password_reset_tokens.py
# 幂等：SHOW TABLES 判表是否已存在，SHOW COLUMNS 兜底判关键列
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import AsyncSessionLocal

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    token_hash CHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_password_reset_token_hash (token_hash),
    KEY idx_password_reset_tokens_user (user_id),
    CONSTRAINT fk_password_reset_tokens_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


async def main():
    async with AsyncSessionLocal() as s:
        # 1) 表是否已存在
        tables = (await s.execute(text("SHOW TABLES LIKE 'password_reset_tokens'"))).all()
        if tables:
            # 2) 兜底：关键列是否齐全（缺列则补建）
            cols = (await s.execute(text("SHOW COLUMNS FROM password_reset_tokens"))).all()
            if any(r[0] == "token_hash" for r in cols):
                print("[跳过] password_reset_tokens 表已存在")
                return

        await s.execute(text(CREATE_TABLE_SQL))
        await s.commit()
        print("已创建表 password_reset_tokens")

        rows = (await s.execute(text("SHOW TABLES LIKE 'password_reset_tokens'"))).all()
        print("当前表:", [r[0] for r in rows])


if __name__ == "__main__":
    asyncio.run(main())
