import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PasswordResetToken, User
from app.schemas import ApiResponse
from app.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_access_token
from app.core.ratelimit import login_limiter
from app.services.email import send_password_reset_email, smtp_configured

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["认证"],
)


def _client_ip(request: Request) -> str:
    # 直接部署取 socket 地址；若置于反向代理后需改为读取 X-Forwarded-For（并信任代理）
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=ApiResponse[TokenResponse])
async def register(req: UserRegisterRequest, request: Request, session: AsyncSession = Depends(get_db)):
    ip = _client_ip(request)
    login_limiter.check_register(ip)
    # 检查用户名是否已存在
    existing = await session.execute(
        select(User).where((User.username == req.username) | (User.email == req.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    login_limiter.record_register(ip)

    token = create_access_token({"sub": str(user.id), "username": user.username})
    return ApiResponse(data=TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    ))


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(req: UserLoginRequest, request: Request, session: AsyncSession = Depends(get_db)):
    ip = _client_ip(request)
    login_limiter.check_login(ip, req.username)
    result = await session.execute(
        select(User).where(User.username == req.username)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        login_limiter.record_login_failure(ip, req.username)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    login_limiter.clear_login(ip, req.username)
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return ApiResponse(data=TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    ))


# ---------- 忘记密码 ----------

# 简单 per-IP 限流：同一 IP 10 分钟内最多 5 次 forgot 请求，防滥用/枚举
_forgot_attempts: dict[str, list[float]] = {}


def _forgot_limiter(ip: str) -> None:
    import time

    now = time.time()
    window = 600  # 10 分钟
    recent = [t for t in _forgot_attempts.get(ip, []) if now - t < window]
    if len(recent) >= 5:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    recent.append(now)
    _forgot_attempts[ip] = recent


def _hash_token(token: str) -> str:
    """token 只存 sha256 哈希，绝不存明文。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/password/forgot", response_model=ApiResponse)
async def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """忘记密码：按邮箱生成一次性重置令牌。

    - SMTP 未配置（dev 模式）：响应 data 返回 reset_token 明文，便于本地全链路测试；
    - SMTP 已配置：真实发送邮件，data 为 None。
    用户不存在时也返回相同文案（防邮箱枚举）。
    """
    ip = _client_ip(request)
    _forgot_limiter(ip)

    user = (
        await session.execute(select(User).where(User.email == req.email))
    ).scalar_one_or_none()

    if user is not None:
        token = secrets.token_urlsafe(32)
        session.add(PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ))
        await session.commit()

        if smtp_configured():
            send_password_reset_email(user.email, token)
            return ApiResponse(data=None, message="若该邮箱已注册，重置链接已发送")
        # dev 模式：未配置 SMTP，直接回传明文 token 便于测试
        return ApiResponse(data={"reset_token": token, "dev": True}, message="开发模式：重置令牌已生成")

    # 用户不存在：返回与成功一致的文案，避免暴露邮箱是否注册
    return ApiResponse(data=None, message="若该邮箱已注册，重置链接已发送")


@router.post("/password/reset", response_model=ApiResponse)
async def reset_password(
    req: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    """使用一次性令牌重置密码。校验 token 有效（未用、未过期）后更新密码，
    并刷新 password_changed_at 使该用户所有旧 token 立即失效。"""
    token_hash = _hash_token(req.token)
    record = (
        await session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
    ).scalar_one_or_none()

    if record is None or record.used_at is not None:
        raise HTTPException(status_code=400, detail="重置令牌无效或已使用")

    now = datetime.now(timezone.utc)
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now > expires:
        raise HTTPException(status_code=400, detail="重置令牌已过期")

    user = (
        await session.execute(select(User).where(User.id == record.user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="用户不存在")

    user.password_hash = hash_password(req.new_password)
    user.password_changed_at = now
    record.used_at = now
    await session.commit()
    return ApiResponse(data=None, message="密码已重置，请使用新密码登录")
