"""
仓储包

统一导出各业务域仓储类，便于依赖注入与上层服务调用。
"""

from app.repositories.base import BaseRepository
from app.repositories.image_repo import ImageRepository
from app.repositories.style_repo import StyleRepository

__all__ = ["BaseRepository", "ImageRepository", "StyleRepository"]
