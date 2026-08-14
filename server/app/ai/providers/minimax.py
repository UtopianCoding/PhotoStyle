"""
MiniMax 图像生成 Provider

占位实现：接口尚未对接，调用即抛 NotImplementedError。
待接入 MiniMax 图像生成 API 后替换为真实逻辑。
"""

from typing import NoReturn

from app.ai.providers.base import ImageProvider
from app.ai.schemas import ImageProviderRequest, ImageProviderResponse
from app.config import settings


class MinimaxProvider(ImageProvider):
    """MiniMax Provider（占位）"""

    def get_provider_id(self) -> str:
        return "minimax"

    def is_available(self) -> bool:
        # 只要配置了 API Key 即视为可用
        return bool(settings.minimax.api_key.get_secret_value())

    async def generate_image(self, request: ImageProviderRequest) -> NoReturn:
        # 接口未实现，统一抛出异常
        raise NotImplementedError("MiniMax Provider 暂未实现")
