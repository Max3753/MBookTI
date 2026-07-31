from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import ApiResponse
from app.schemas.user import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_access_token

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["认证"],
)


@router.post("/register", response_model=ApiResponse[TokenResponse])
async def register(req: UserRegisterRequest, session: AsyncSession = Depends(get_db)):
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

    token = create_access_token({"sub": str(user.id), "username": user.username})
    return ApiResponse(data=TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    ))


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(req: UserLoginRequest, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(User).where(User.username == req.username)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token({"sub": str(user.id), "username": user.username})
    return ApiResponse(data=TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    ))
