"""
存储提供商统一接口

所有存储适配器（MinIO / OSS / 未来扩展）均实现此接口，
上层服务通过 StorageProvider 操作对象存储，无需关心底层实现差异。
"""

from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """对象存储统一接口"""

    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str) -> str:
        """
        上传对象并返回公开访问 URL

        Args:
            key: 对象存储 key（如 images/userId/20260812/xxx.jpg）
            data: 文件字节流
            content_type: MIME 类型

        Returns:
            对象的公开访问 URL
        """
        pass

    def fetch_and_store(self, url: str, key: str, content_type: str) -> str:
        """
        从远程 URL 获取文件并存储到对象存储，返回公开访问 URL。

        默认实现：下载到内存后上传。子类可覆写为服务端直接复制（如 OSS put_object_from_url），
        省去本地下载环节，节省 2-10 秒。

        Args:
            url: 远程文件 URL
            key: 对象存储 key
            content_type: MIME 类型

        Returns:
            对象的公开访问 URL
        """
        import httpx

        resp = httpx.get(url, timeout=60.0, follow_redirects=True)
        resp.raise_for_status()
        return self.upload(key, resp.content, content_type)

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        删除对象

        Args:
            key: 对象存储 key
        """
        pass

    @abstractmethod
    def get_public_url(self, key: str) -> str:
        """
        根据对象 key 生成公开访问 URL

        Args:
            key: 对象存储 key

        Returns:
            公开访问 URL
        """
        pass

    @staticmethod
    def extract_key_from_url(url: str, bucket: str) -> str:
        """
        从公开 URL 中提取对象 key

        Args:
            url: 公开访问 URL
            bucket: 存储桶名称

        Returns:
            对象 key
        """
        bucket_path = f"/{bucket}/"
        idx = url.find(bucket_path)
        if idx >= 0:
            return url[idx + len(bucket_path):]
        return url
