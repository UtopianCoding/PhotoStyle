"""
Provider 管理器

负责注册、选择与回退图像生成 Provider：
- 按 provider_id 精确选择；
- 不可用时按 fallback_chain 顺序回退到下一个可用 Provider。
- 支持多 Provider 并发调用（generate_multi）。
"""

import asyncio
import logging
from typing import Iterable

from app.ai.providers.base import ImageProvider
from app.ai.providers.dalle import DalleProvider
from app.ai.providers.doubao import DoubaoProvider
from app.ai.providers.minimax import MinimaxProvider
from app.ai.providers.qianwen import QianwenProvider
from app.ai.providers.volcengine import VolcengineProvider
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
            defaults = [QianwenProvider(), DoubaoProvider(), DalleProvider(), MinimaxProvider(), VolcengineProvider()]

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
        # 若未指定 preferred，使用管理后台配置的默认 Provider
        if not preferred:
            from app.services.model_config_store import model_config_store
            preferred = model_config_store.get_default_provider()
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

    async def generate_multi(
        self,
        request: ImageProviderRequest,
        providers: list[str] | None = None,
    ) -> list[tuple[str, ImageProviderResponse]]:
        """
        并发调用多个 Provider 进行图像生成。

        Args:
            request: 统一请求对象
            providers: 要调用的 Provider ID 列表；为空时从配置读取启用的 Provider

        Returns:
            [(provider_id, response), ...] 成功调用的结果列表

        Raises:
            AIServiceException: 所有 Provider 均失败或不可用
        """
        # 确定要调用的 Provider 列表
        if not providers:
            from app.services.model_config_store import model_config_store
            providers = model_config_store.get_enabled_providers()

        if not providers:
            raise AIServiceException("未配置任何启用的 Provider")

        # 过滤出可用的 Provider
        available: list[str] = []
        for pid in providers:
            provider = self._providers.get(pid)
            if provider and provider.is_available():
                available.append(pid)
            else:
                logger.warning("Provider [%s] 不可用，跳过", pid)

        if not available:
            raise AIServiceException(f"所有指定的 Provider 均不可用: {providers}")

        logger.info("并发调用 Provider: %s", available)

        # 并发调用所有可用的 Provider
        async def _call_one(pid: str) -> tuple[str, ImageProviderResponse | None, str | None]:
            """调用单个 Provider，返回 (pid, response, error)"""
            provider = self._providers[pid]
            try:
                response = await provider.generate_image(request)
                return pid, response, None
            except NotImplementedError as exc:
                logger.warning("Provider [%s] 未实现: %s", pid, exc)
                return pid, None, f"{pid}: 未实现"
            except AIServiceException as exc:
                logger.warning("Provider [%s] 调用失败: %s", pid, exc.message)
                return pid, None, f"{pid}: {exc.message}"
            except Exception as exc:
                logger.exception("Provider [%s] 发生未预期异常", pid)
                return pid, None, f"{pid}: {exc}"

        results = await asyncio.gather(*[_call_one(pid) for pid in available])

        # 收集成功的结果
        successes: list[tuple[str, ImageProviderResponse]] = []
        errors: list[str] = []
        for pid, response, error in results:
            if response is not None:
                successes.append((pid, response))
            elif error:
                errors.append(error)

        if not successes:
            raise AIServiceException(
                f"所有 Provider 均调用失败: {'; '.join(errors)}"
            )

        logger.info(
            "多 Provider 调用完成: 成功=%d, 失败=%d",
            len(successes), len(errors),
        )
        return successes
