# 全局异常处理器
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常，返回统一格式"""
    return JSONResponse(
        status_code=500,
        content={"data": None, "error": "服务器内部错误，请稍后重试"},
    )


async def http_exception_handler(request: Request, exc):
    """HTTPException 保持原有状态码"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"data": None, "error": exc.detail},
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """数据库异常，不暴露具体信息"""
    return JSONResponse(
        status_code=500,
        content={"data": None, "error": "数据库操作失败"},
    )
