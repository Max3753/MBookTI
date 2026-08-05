from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.schemas.datetime_utils import UtcDatetime


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
    created_at: UtcDatetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserStats(BaseModel):
    comment_count: int = 0
    favorite_count: int = 0
    like_received: int = 0
    # 关注统计（公开主页使用；默认 0，向后兼容老客户端）
    follower_count: int = 0
    following_count: int = 0


class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    avatar_url: Optional[str] = None
    mbti_type_id: Optional[int] = None
    mbti_type_code: Optional[str] = None
    mbti_type_name: Optional[str] = None
    is_admin: bool = False
    # 公开主页开关（个人中心可改；仅自己可见时他人访问主页相关接口返回 404）
    is_profile_public: bool = True
    created_at: UtcDatetime
    stats: UserStats


class PublicUserProfileResponse(BaseModel):
    """公开用户主页（无需登录即可访问）。

    刻意不继承 UserProfileResponse：Pydantic v2 无法通过继承删除 email 字段，
    公开接口必须避免泄露邮箱，因此独立定义（字段形状对齐 UserProfileResponse 减去 email）。
    额外携带 is_following / is_self 表示当前登录者与该用户的关系。
    """
    id: int
    username: str
    avatar_url: Optional[str] = None
    is_admin: bool = False
    is_profile_public: bool = True
    created_at: UtcDatetime
    mbti_type_code: Optional[str] = None
    mbti_type_name: Optional[str] = None
    stats: UserStats
    is_following: bool = False
    is_self: bool = False


class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_\u4e00-\u9fa5-]+$")
    avatar_url: Optional[str] = Field(None, max_length=2048)
    mbti_type_id: Optional[int] = None
    is_profile_public: Optional[bool] = None


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
