import json
import re

import httpx

SEARCH_URL = "https://search.douban.com/book/subject_search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://book.douban.com/",
}


def _normalize(s: str) -> str:
    """去除空格和常见符号，用于模糊匹配"""
    return re.sub(r"[\s·\-—:：,，.。\"'“”]+", "", s or "")


def _extract_json(html: str) -> dict | None:
    """从 window.__DATA__ = {...} 中按括号配平提取完整 JSON。

    豆瓣 JSON 含嵌套结构，非贪婪正则会在第一个 } 处截断导致解析失败，
    必须数大括号配平到真正的结尾。
    """
    start = html.find("window.__DATA__")
    if start == -1:
        return None
    i = html.find("{", start)
    if i == -1:
        return None
    depth = 0
    for j in range(i, len(html)):
        c = html[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[i : j + 1])
    return None


async def search_cover(title: str, author: str) -> str | None:
    """根据书名和作者搜索豆瓣封面。

    豆瓣搜索页改版后 items 只含轻量信息（title/url/tpl_name），封面在详情页。
    因此需要两级请求：
      1. 搜索页（带作者提升命中率）→ 匹配书名 → 拿到详情页 /subject/ 链接
      2. 详情页 → 提取 <meta property="og:image"> 封面
    任何一步失败都返回 None，由调用方降级为占位图。
    """
    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS, follow_redirects=True) as client:
            # 第一级：搜索页
            resp = await client.get(
                SEARCH_URL,
                params={
                    "search_text": " ".join(filter(None, [title, author])),
                    "cat": 1001,
                },
            )
            if resp.status_code != 200:
                return None

            data = _extract_json(resp.text)
            if not data:
                return None

            # 匹配书名，只取书详情页链接（跳过 series 丛书页等）
            target_title = _normalize(title)
            detail_url = None
            for item in data.get("items") or []:
                url = item.get("url") or ""
                if not url.startswith("https://book.douban.com/subject/"):
                    continue
                item_title = _normalize(item.get("title") or "")
                if target_title not in item_title and item_title not in target_title:
                    continue
                detail_url = url
                break
            if not detail_url:
                return None

            # 第二级：详情页提取 og:image
            r2 = await client.get(detail_url)
            if r2.status_code != 200:
                return None
            og = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', r2.text)
            return og.group(1) if og else None
    except Exception:
        return None