"""
OpenAI DALL-E 图像生成 Provider

占位实现：接口尚未对接，调用即抛 NotImplementedError。
待接入 OpenAI DALL-E API 后替换为真实逻辑。
"""

from typing import NoReturn

from app.ai.providers.base import ImageProvider
from app.ai.schemas import ImageProviderRequest, ImageProviderResponse
from app.services.model_config_store import model_config_store


class DalleProvider(ImageProvider):
    """OpenAI DALL-E Provider（占位）"""

    def get_provider_id(self) -> str:
        return "dalle"

    def is_available(self) -> bool:
        cfg = model_config_store.get_config("dalle") or {}
        return bool(cfg.get("api_key"))

    async def generate_image(self, request: ImageProviderRequest) -> NoReturn:
        raise NotImplementedError("OpenAI DALL-E Provider 暂未实现")
