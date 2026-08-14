"""
Provider 管理器

负责注册、选择与回退图像生成 Provider：
- 按 provider_id 精确选择；
- 不可用时按 fallback_chain 顺序回退到下一个可用 Provider。
"""

import logging
from typing import Iterable

from app.ai.providers.base import ImageProvider
from app.ai.providers.dalle import DalleProvider
from app.ai.providers.doubao import DoubaoProvider
from app.ai.providers.minimax import MinimaxProvider
from app.ai.providers.qianwen import QianwenProvider
from app.ai.schemas import ImageProviderRequest, ImageProviderResponse
from app.core.exceptions import AIServiceException

logger = logging.getLogger(__name__)


class ProviderManager:
    """Provider 注册中心与调度器"""

    def __init__(self, providers: Iterable[ImageProvider] | None = None) -> None:
        # provider_id -> ImageProvider
        self._providers: dict[str, ImageProvider] = {}
        # 默认回退链
        self._fallback_chain: list[str] = []

        # 注册默认 Provider
        defaults: list[ImageProvider] = list(providers or [])
        if not defaults:
            defaults = [QianwenProvider(), DoubaoProvider(), DalleProvider(), MinimaxProvider()]

        for p in defaults:
            self.register(p, append_fallback=True)

    # -------------------- 注册 --------------------

    def register(self, provider: ImageProvider, append_fallback: bool = True) -> None:
        """注册 Provider，并可选加入默认回退链"""
        pid = provider.get_provider_id()
        self._providers[pid] = provider
        if append_fallback and pid not in self._fallback_chain:
            self._fallback_chain.append(pid)

    def set_fallback_chain(self, chain: list[str]) -> None:
        """显式设置回退链顺序"""
        self._fallback_chain = [pid for pid in chain if pid in self._providers]

    # -------------------- 查询 --------------------

    def get_provider(self, provider_id: str) -> ImageProvider | None:
        """按 ID 获取已注册 Provider"""
        return self._providers.get(provider_id)

    def list_available(self) -> list[ImageProvider]:
        """列出所有当前可用的 Provider"""
        return [p for p in self._providers.values() if p.is_available()]

    # -------------------- 调度 --------------------

    async def generate(
        self,
        request: ImageProviderRequest,
        preferred: str | None = None,
    ) -> ImageProviderResponse:
        """
        调度图像生成。

        Args:
            request: 统一请求对象
            preferred: 优先使用的 Provider ID；为空则使用回退链首个可用

        Returns:
            首个成功的 Provider 的响应

        Raises:
            AIServiceException: 所有 Provider 均不可用或全部失败
        """
        # 构造尝试顺序：优先 Provider 在前，其后跟回退链
        order: list[str] = []
        if preferred and preferred in self._providers:
            order.append(preferred)
        for pid in self._fallback_chain:
            if pid not in order:
                order.append(pid)

        errors: list[str] = []
        for pid in order:
            provider = self._providers[pid]
            if not provider.is_available():
                logger.debug("Provider [%s] 不可用，跳过", pid)
                continue
            try:
                logger.info("使用 Provider [%s] 进行图像生成", pid)
                response = await provider.generate_image(request)
                return response
            except NotImplementedError as exc:
                # 未实现的 Provider 直接跳过，不影响回退
                logger.warning("Provider [%s] 未实现: %s", pid, exc)
                errors.append(f"{pid}: {exc}")
            except AIServiceException as exc:
                logger.warning("Provider [%s] 调用失败: %s", pid, exc.message)
                errors.append(f"{pid}: {exc.message}")
            except Exception as exc:
                logger.exception("Provider [%s] 发生未预期异常", pid)
                errors.append(f"{pid}: {exc}")

        raise AIServiceException(
            f"所有可用 Provider 均调用失败: {'; '.join(errors) or '无可用 Provider'}"
        )
