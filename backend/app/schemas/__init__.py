from app.schemas.common import ApiResponse, ApiListResponse, ErrorResponse
from app.schemas.mbti_type import MbtiTypeResponse
from app.schemas.book import (
    BookResponse,
    BookDetailResponse,
    RecommendedTypeInfo,
    BookRatingRequest,
    BookRatingResponse,
)
from app.schemas.recommendation import RecommendationResponse, AIGenerateRequest, AIGenerateBook
from app.schemas.user import (
    UserResponse,
    TokenResponse,
    UserRegisterRequest,
    UserLoginRequest,
    UserProfileResponse,
    PublicUserProfileResponse,
    UserStats,
    UserUpdateRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    AdminResetPasswordRequest,
)
from app.schemas.comment import CommentResponse, CommentCreateRequest, MyCommentResponse
from app.schemas.community import FeedItem
from app.schemas.announcement import AnnouncementResponse, AnnouncementCreateRequest
from app.schemas.notification import NotificationResponse, NotificationCreateRequest, UnreadCountResponse
from app.schemas.reading_record import (
    ProgressSaveRequest,
    ReadingRecordResponse,
)

__all__ = [
    "ApiResponse",
    "ApiListResponse",
    "ErrorResponse",
    "MbtiTypeResponse",
    "BookResponse",
    "BookDetailResponse",
    "RecommendedTypeInfo",
    "BookRatingRequest",
    "BookRatingResponse",
    "RecommendationResponse",
    "AIGenerateRequest",
    "AIGenerateBook",
    "UserResponse",
    "TokenResponse",
    "UserRegisterRequest",
    "UserLoginRequest",
    "UserProfileResponse",
    "PublicUserProfileResponse",
    "UserStats",
    "UserUpdateRequest",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "AdminResetPasswordRequest",
    "CommentResponse",
    "CommentCreateRequest",
    "MyCommentResponse",
    "FeedItem",
    "AnnouncementResponse",
    "AnnouncementCreateRequest",
    "NotificationResponse",
    "NotificationCreateRequest",
    "UnreadCountResponse",
    "ProgressSaveRequest",
    "ReadingRecordResponse",
]
