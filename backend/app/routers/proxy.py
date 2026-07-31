from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from urllib.parse import urlparse
import httpx

router = APIRouter(prefix="/api/v1/proxy", tags=["代理"])

# 豆瓣图床要求带豆瓣站点 Referer + 完整浏览器 UA 才放行（缺 UA 会被识别为非浏览器请求返回 418）
_DOUBAN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://book.douban.com/",
}


def _is_douban_cover_url(url: str) -> bool:
    """严格校验目标为豆瓣图床封面：https + img[N].doubanio.com。

    防 SSRF：域名精确匹配白名单，拒绝重定向目标无关的 host、IP、端口、userinfo。
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    # 仅允许 https
    if parsed.scheme != "https":
        return False
    # 拒绝显式端口（默认 443 时 parsed.port 为 None）
    if parsed.port is not None:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    # 豆瓣图床域名：img.doubanio.com 或 imgN.doubanio.com（N 为纯数字，如 img1/img2）
    if not host.endswith(".doubanio.com") or not host.startswith("img"):
        return False
    label = host[len("img"):-len(".doubanio.com")]
    if label and not label.isdigit():
        return False
    return True


@router.get("/cover")
async def proxy_cover(url: str = Query(...)):
    """代理豆瓣封面图，绕过图床防盗链。

    浏览器直接 <img src="imgN.doubanio.com"> 会带 localhost Referer 被 403/418，
    改由后端代拿（带豆瓣 Referer），前端同源加载，一劳永逸。
    """
    # 仅允许豆瓣图床地址，防 SSRF
    if not _is_douban_cover_url(url):
        raise HTTPException(status_code=400, detail="仅允许代理豆瓣图床地址")
    try:
        async with httpx.AsyncClient(timeout=15, headers=_DOUBAN_HEADERS) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="豆瓣图床请求失败")
            return Response(
                content=resp.content,
                media_type=resp.headers.get("content-type", "image/jpeg"),
                headers={"Cache-Control": "public, max-age=86400"},  # 浏览器缓存 1 天，减少代理压力
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="代理请求失败")
