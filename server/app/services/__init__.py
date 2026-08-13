"""
服务包

统一导出各业务域服务类，便于依赖注入与 API 层调用。
"""

from app.services.auth_service import AuthService
from app.services.history_service import HistoryService
from app.services.image_service import ImageService
from app.services.style_service import StyleService, process_style_task

__all__ = [
    "AuthService",
    "HistoryService",
    "ImageService",
    "StyleService",
    "process_style_task",
]
