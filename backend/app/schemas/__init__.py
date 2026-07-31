from app.schemas.common import ApiResponse, ApiListResponse, ErrorResponse
from app.schemas.mbti_type import MbtiTypeResponse
from app.schemas.book import BookResponse, BookDetailResponse, RecommendedTypeInfo
from app.schemas.recommendation import RecommendationResponse, AIGenerateRequest, AIGenerateBook
from app.schemas.user import UserResponse, TokenResponse, UserRegisterRequest, UserLoginRequest
from app.schemas.comment import CommentResponse, CommentCreateRequest

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
    "CommentResponse",
    "CommentCreateRequest",
]
