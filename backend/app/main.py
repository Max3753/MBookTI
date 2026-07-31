from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from app.config import settings
from app.database import AsyncSessionLocal
from app.seed.mbti_types import init_mbti_types
from app.core.exceptions import global_exception_handler, http_exception_handler, sqlalchemy_exception_handler

from app.routers import mbti_types, recommendations, books, auth, comments, proxy

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
)

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

@app.get("/health")
async def health():
    return {"status": "ok"}