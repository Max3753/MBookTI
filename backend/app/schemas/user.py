from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_\u4e00-\u9fa5-]+$")
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    avatar_url: Optional[str] = None
    mbti_type_id: Optional[int] = None
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserStats(BaseModel):
    comment_count: int = 0
    favorite_count: int = 0
    like_received: int = 0


class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    avatar_url: Optional[str] = None
    mbti_type_id: Optional[int] = None
    mbti_type_code: Optional[str] = None
    mbti_type_name: Optional[str] = None
    is_admin: bool = False
    created_at: datetime
    stats: UserStats


class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_\u4e00-\u9fa5-]+$")
    avatar_url: Optional[str] = Field(None, max_length=2048)
    mbti_type_id: Optional[int] = None


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=6, max_length=128)


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)
