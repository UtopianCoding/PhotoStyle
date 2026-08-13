"""
存储工厂

根据 settings.storage.type 选择对应的存储适配器。
支持 "minio" 和 "oss" 两种类型，可通过环境变量 STORAGE_TYPE 切换。
"""

import logging

from app.config import settings
from app.core.exceptions import StorageException
from app.core.storage.base import StorageProvider

logger = logging.getLogger(__name__)

# 缓存单例，避免重复创建客户端
_provider_instance: StorageProvider | None = None


def get_storage_provider() -> StorageProvider:
    """
    获取存储适配器单例

    根据 STORAGE_TYPE 环境变量返回对应的存储适配器：
    - "minio"：返回 MinIOProvider（默认，适用于本地开发）
    - "oss"：返回 OSSProvider（适用于生产环境）

    Returns:
        StorageProvider 实例

    Raises:
        StorageException: 不支持的存储类型
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    storage_type = settings.storage.type.lower().strip()

    if storage_type == "minio":
        from app.core.storage.minio_provider import MinIOProvider
        _provider_instance = MinIOProvider()
        logger.info("存储适配器: MinIO (endpoint=%s, bucket=%s)", settings.minio.endpoint, settings.minio.bucket)
    elif storage_type == "oss":
        from app.core.storage.oss_provider import OSSProvider
        _provider_instance = OSSProvider()
        logger.info("存储适配器: OSS (endpoint=%s, bucket=%s)", settings.oss.endpoint, settings.oss.bucket)
    else:
        raise StorageException(f"不支持的存储类型: {storage_type}，可选值: minio / oss")

    return _provider_instance
