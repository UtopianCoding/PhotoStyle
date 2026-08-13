"""
Pydantic 模式包

统一导出各业务域请求/响应模式，便于 API 层与服务层引用。
"""

from app.schemas.common import ApiResponse, PageResponse
from app.schemas.history import HistoryDetail, HistoryItem, HistoryListResponse
from app.schemas.image import ImageDeleteResponse, ImageInfo, ImageUploadResponse
from app.schemas.style import (
    ConvertRequest,
    ConvertResponse,
    StyleOptions,
    TaskResult,
    TaskStatusResponse,
)
from app.schemas.user import TokenResponse, UserInfo, UserLogin, UserRegister

__all__ = [
    "ApiResponse",
    "PageResponse",
    "ImageUploadResponse",
    "ImageInfo",
    "ImageDeleteResponse",
    "ConvertRequest",
    "ConvertResponse",
    "StyleOptions",
    "TaskResult",
    "TaskStatusResponse",
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "UserInfo",
    "HistoryItem",
    "HistoryListResponse",
    "HistoryDetail",
]
