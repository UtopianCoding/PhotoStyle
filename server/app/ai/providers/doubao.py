"""
火山引擎豆包（Doubao）图像生成 Provider

占位实现：接口尚未对接，调用即抛 NotImplementedError。
待接入火山引擎豆包 API 后替换为真实逻辑。
"""

from typing import NoReturn

from app.ai.providers.base import ImageProvider
from app.ai.schemas import ImageProviderRequest, ImageProviderResponse
from app.services.model_config_store import model_config_store


class DoubaoProvider(ImageProvider):
    """火山引擎豆包 Provider（占位）"""

    def get_provider_id(self) -> str:
        return "doubao"

    def is_available(self) -> bool:
        cfg = model_config_store.get_config("doubao") or {}
        return bool(cfg.get("access_key") and cfg.get("secret_key"))

    async def generate_image(self, request: ImageProviderRequest) -> NoReturn:
        raise NotImplementedError("火山引擎豆包 Provider 暂未实现")
