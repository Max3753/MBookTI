# 数据库模型初始化
from app.models.base import Base
from app.models.mbti_type import MbtiType
from app.models.book import Book
from app.models.recommendation import Recommendation
from app.models.user import User
from app.models.comment import Comment
from app.models.comment_like import CommentLike
from app.models.favorite import UserBookFavorite
from app.models.announcement import Announcement, AnnouncementAck
from app.models.notification import Notification
from app.models.password_reset_token import PasswordResetToken
from app.models.reading_record import ReadingRecord
