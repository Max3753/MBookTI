# 共享时间类型：把数据库中的 naive datetime（统一为 UTC）序列化为带时区偏移的 ISO8601。
#
# 背景：MySQL 8 容器默认时区为 UTC，server_default=func.now() 存的是无时区标记的 UTC 时间；
# 若直接序列化，前端 new Date("2026-08-03T02:15:00") 会按浏览器本地时区解读，导致 UTC+8 用户
# 看到"8 小时前"。本类型在 JSON 序列化时补上 +00:00 偏移，前端即可正确换算成本地时间。
from datetime import datetime, timezone
from typing import Annotated
from pydantic import PlainSerializer


def _serialize_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


# Pydantic v2 Annotated 类型：校验阶段仍接受任意 datetime，序列化时统一输出 UTC ISO8601。
UtcDatetime = Annotated[
    datetime,
    PlainSerializer(_serialize_utc, return_type=str, when_used="always"),
]
