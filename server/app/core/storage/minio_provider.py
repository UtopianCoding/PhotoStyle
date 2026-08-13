"""
MinIO 存储适配器

基于 minio SDK 实现 StorageProvider 接口。
适用于本地开发和自托管场景。
"""

import io
import logging

from app.config import settings
from app.core.exceptions import StorageException
from app.core.storage.base import StorageProvider

logger = logging.getLogger(__name__)


class MinIOProvider(StorageProvider):
    """MinIO 存储适配器"""

    def __init__(self) -> None:
        from minio import Minio

        access_key = settings.minio.access_key.get_secret_value()
        secret_key = settings.minio.secret_key.get_secret_value()
        if not access_key or not secret_key:
            raise StorageException("MinIO 凭证未配置")

        self._client = Minio(
            endpoint=settings.minio.endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=settings.minio.secure,
        )
        self._bucket = settings.minio.bucket
        self._public_base_url = settings.minio.public_base_url.rstrip("/")

    def _ensure_bucket(self) -> None:
        """
        确保存储桶存在（不存在则创建）。

        对于权限受限的 IAM 用户，bucket_exists() 可能抛出 AccessDenied，
        此时跳过检查，直接尝试上传（put_object 会自动创建桶或直接成功）。
        """
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
                logger.info("MinIO 存储桶已创建: %s", self._bucket)
        except Exception as exc:
            # AccessDenied / 权限不足时跳过检查，后续 put_object 会验证实际权限
            logger.warning(
                "MinIO bucket_exists 检查失败（可能权限受限）: %s, bucket=%s",
                exc, self._bucket,
            )

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        """上传对象到 MinIO，返回公开 URL"""
        self._ensure_bucket()
        stream = io.BytesIO(data)
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=key,
            data=stream,
            length=len(data),
            content_type=content_type,
        )
        logger.debug("MinIO 上传成功: %s", key)
        return self.get_public_url(key)

    def delete(self, key: str) -> None:
        """删除 MinIO 对象"""
        try:
            self._client.remove_object(self._bucket, key)
        except Exception as exc:
            logger.warning("MinIO 删除失败: %s, err=%s", key, exc)

    def get_public_url(self, key: str) -> str:
        """拼接 MinIO 公开访问 URL"""
        return f"{self._public_base_url}/{self._bucket}/{key}"

    def extract_key_from_url(self, url: str) -> str:
        """从公开 URL 中提取对象 key"""
        return StorageProvider.extract_key_from_url(url, self._bucket)
