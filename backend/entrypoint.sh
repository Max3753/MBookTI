#!/bin/sh
set -e

echo "==> 等待数据库就绪..."
# 简单等待：Mysql 勇气健康价差通过后才会启动 backend （间 compose 的 depends_on）
# 这里再兜底等待端口连接
python - <<'EOF'
import asyncio, sys
sys.path.insert(0, '/app')
from sqlalchemy import text
from app.database import async_engine

async def wait_db():
    for i in range(30):
        try:
            async with async_engine.connect() as conn:
                await conn.execute(text('SELECT 1'))

            print('数据库已就绪')
            return
        except Exception as e:
            print(f"等待数据库连接 ({i+1}/30)：{e}")
            await asyncio.sleep(2)

    # 30 次全部失败才退出（缩进在 for 循环外）
    raise SystemExit("数据库连接超时")

asyncio.run(wait_db())
EOF

echo "==> 建表 (幂等，只创建缺失表) ..."
python scripts/create_notification_tables.py
python scripts/create_reading_record_tables.py
python scripts/create_social_tables.py

echo "==> 启动后端 ..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 


