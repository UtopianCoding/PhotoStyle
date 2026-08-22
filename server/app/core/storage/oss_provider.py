"""
阿里云 OSS 存储适配器

基于 oss2 SDK 实现 StorageProvider 接口。
适用于生产环境使用阿里云 OSS 的场景。
"""

import logging

from app.config import settings
from app.core.exceptions import StorageException
from app.core.storage.base import StorageProvider

logger = logging.getLogger(__name__)


class OSSProvider(StorageProvider):
    """阿里云 OSS 存储适配器"""

    def __init__(self) -> None:
        import oss2

        key_id = settings.oss.access_key_id.get_secret_value()
        key_secret = settings.oss.access_key_secret.get_secret_value()
        if not key_id or not key_secret:
            raise StorageException("OSS 凭证未配置")

        auth = oss2.Auth(key_id, key_secret)
        self._bucket = oss2.Bucket(auth, settings.oss.endpoint, settings.oss.bucket)
        self._bucket_name = settings.oss.bucket
        self._endpoint = settings.oss.endpoint

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        """上传对象到 OSS，返回公开 URL"""
        headers = {"Content-Type": content_type}
        result = self._bucket.put_object(key, data, headers=headers)
        status = getattr(result, "status", 200)
        if status < 200 or status >= 300:
            raise StorageException(f"OSS 上传失败: status={status}")
        logger.debug("OSS 上传成功: %s", key)
        return self.get_public_url(key)

    def fetch_and_store(self, url: str, key: str, content_type: str) -> str:
        """
        使用 OSS 服务端直接拉取远程 URL 存储，省去本地下载环节。

        通过 oss2 的 put_object_from_url 实现服务端复制（阿里云内网更快），
        失败时回退到默认的下载+上传。
        """
        try:
            headers = {"Content-Type": content_type}
            self._bucket.put_object_from_url(key, url, headers=headers)
            logger.debug("OSS 服务端复制成功: %s <- %s", key, url)
            return self.get_public_url(key)
        except Exception as exc:
            logger.warning("OSS 服务端复制失败，回退下载+上传: %s", exc)
            return super().fetch_and_store(url, key, content_type)

    def delete(self, key: str) -> None:
        """删除 OSS 对象"""
        try:
            self._bucket.delete_object(key)
        except Exception as exc:
            logger.warning("OSS 删除失败: %s, err=%s", key, exc)

    def get_public_url(self, key: str) -> str:
        """拼接 OSS 公开访问 URL"""
        endpoint = self._endpoint.replace("https://", "").replace("http://", "")
        return f"https://{self._bucket_name}.{endpoint}/{key}"

    def extract_key_from_url(self, url: str) -> str:
        """从公开 URL 中提取对象 key"""
        return StorageProvider.extract_key_from_url(url, self._bucket_name)
