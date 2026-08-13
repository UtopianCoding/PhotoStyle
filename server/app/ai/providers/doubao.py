"""
火山引擎豆包（Doubao）Provider

占位实现：接口尚未对接，调用即抛 NotImplementedError。
待接入火山引擎视觉/图像生成 API 后替换为真实逻辑。
"""

from typing import NoReturn

from app.ai.providers.base import ImageProvider
from app.ai.schemas import ImageProviderRequest, ImageProviderResponse
from app.config import settings


class DoubaoProvider(ImageProvider):
    """火山引擎豆包 Provider（占位）"""

    def get_provider_id(self) -> str:
        return "doubao"

    def is_available(self) -> bool:
        # 只要配置了 Access Key / Secret Key 即视为可用（真实接入后细化）
        return bool(
            settings.doubao.access_key.get_secret_value()
            and settings.doubao.secret_key.get_secret_value()
        )

    async def generate_image(self, request: ImageProviderRequest) -> NoReturn:
        # 接口未实现，统一抛出异常
        raise NotImplementedError("豆包 Provider 暂未实现")
