from app.schemas.common import ApiResponse, ApiListResponse, ErrorResponse
from app.schemas.mbti_type import MbtiTypeResponse
from app.schemas.book import BookResponse, BookDetailResponse, RecommendedTypeInfo
from app.schemas.recommendation import RecommendationResponse, AIGenerateRequest, AIGenerateBook
from app.schemas.user import (
    UserResponse,
    TokenResponse,
    UserRegisterRequest,
    UserLoginRequest,
    UserProfileResponse,
    UserStats,
    UserUpdateRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    AdminResetPasswordRequest,
)
from app.schemas.comment import CommentResponse, CommentCreateRequest, MyCommentResponse
from app.schemas.announcement import AnnouncementResponse, AnnouncementCreateRequest
from app.schemas.notification import NotificationResponse, NotificationCreateRequest, UnreadCountResponse

__all__ = [
    "ApiResponse",
    "ApiListResponse",
    "ErrorResponse",
    "MbtiTypeResponse",
    "BookResponse",
    "BookDetailResponse",
    "RecommendedTypeInfo",
    "RecommendationResponse",
    "AIGenerateRequest",
    "AIGenerateBook",
    "UserResponse",
    "TokenResponse",
    "UserRegisterRequest",
    "UserLoginRequest",
    "UserProfileResponse",
    "UserStats",
    "UserUpdateRequest",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "AdminResetPasswordRequest",
    "CommentResponse",
    "CommentCreateRequest",
    "MyCommentResponse",
    "AnnouncementResponse",
    "AnnouncementCreateRequest",
    "NotificationResponse",
    "NotificationCreateRequest",
    "UnreadCountResponse",
]
