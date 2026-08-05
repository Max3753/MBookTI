from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from app.config import settings
from app.database import AsyncSessionLocal
from app.seed.mbti_types import init_mbti_types
from app.core.exceptions import global_exception_handler, http_exception_handler, sqlalchemy_exception_handler

from app.routers import mbti_types, recommendations, books, auth, comments, proxy, users, announcements, notifications, reader, community

# 用户上传文件根目录（头像等）：backend/uploads
UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with AsyncSessionLocal() as session:
            await init_mbti_types(session)
    except Exception as e:
        print(f"[启动警告] 数据库连接失败，跳过初始化: {e}")
    yield
    

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
    # 非调试模式（生产）关闭 API 文档暴露
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# 安全响应头
@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response

# 注册全局异常处理器
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mbti_types.router)
app.include_router(recommendations.router)
app.include_router(books.router)
app.include_router(auth.router)
app.include_router(comments.router)
app.include_router(proxy.router)
app.include_router(users.router)
app.include_router(announcements.router)
app.include_router(notifications.router)
app.include_router(reader.router)
app.include_router(community.router)

# 用户上传文件静态托管（头像等）：/uploads/avatars/xxx.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_ROOT), name="uploads")

@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    # 直接运行（python -m app.main）时监听所有网卡，支持局域网/移动设备访问。
    # 若用 `uvicorn app.main:app` 启动，需手动加 --host 0.0.0.0 才能被局域网访问。
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=5000, reload=True)