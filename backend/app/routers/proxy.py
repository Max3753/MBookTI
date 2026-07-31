from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
import httpx

router = APIRouter(prefix="/api/v1/proxy", tags=["代理"])

# 豆瓣图床要求带豆瓣站点 Referer + 完整浏览器 UA 才放行（缺 UA 会被识别为非浏览器请求返回 418）
_DOUBAN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://book.douban.com/",
}


@router.get("/cover")
async def proxy_cover(url: str = Query(...)):
    """代理豆瓣封面图，绕过图床防盗链。

    浏览器直接 <img src="imgN.doubanio.com"> 会带 localhost Referer 被 403/418，
    改由后端代拿（带豆瓣 Referer），前端同源加载，一劳永逸。
    """
    # 仅允许豆瓣图床地址，防 SSRF
    if not (url.startswith("https://img") and "doubanio.com" in url):
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
