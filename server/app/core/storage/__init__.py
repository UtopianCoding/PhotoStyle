"""
对象存储抽象层

统一导出 StorageProvider 接口、MinIO/OSS 适配器与工厂函数。
通过 STORAGE_TYPE 环境变量选择使用哪种存储方式。
"""

from app.core.storage.base import StorageProvider
from app.core.storage.factory import get_storage_provider

__all__ = [
    "StorageProvider",
    "get_storage_provider",
]
