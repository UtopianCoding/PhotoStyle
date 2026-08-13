"""
AI 图像生成 Provider 抽象基类

定义所有 Provider 必须实现的统一接口，便于 ProviderManager 调度与回退。
"""

from abc import ABC, abstractmethod

from app.ai.schemas import ImageProviderRequest, ImageProviderResponse


class ImageProvider(ABC):
    """图像生成 Provider 抽象接口"""

    @abstractmethod
    def get_provider_id(self) -> str:
        """返回 Provider 唯一标识，如 qianwen / doubao / dalle"""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """
        判断当前 Provider 是否可用（如已配置 API Key）。
        ProviderManager 据此构建可用 Provider 链。
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_image(self, request: ImageProviderRequest) -> ImageProviderResponse:
        """
        调用图像生成接口。

        对于异步任务型接口，应内部轮询至终态后再返回；
        若无法在合理时间内完成，返回 status=pending 并附带 provider_task_id。

        Args:
            request: 统一请求对象

        Returns:
            统一响应对象

        Raises:
            AIServiceException: 调用失败
        """
        raise NotImplementedError
