from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    """统一响应"""
    data: T
    message: str = "success"
    
class ApiListResponse(BaseModel, Generic[T]):
    """列表响应"""
    data: list[T]
    total: int
    message: str = "success"
    
class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    data: None = None
