"""
阿里云千问（Qwen-Image）图像生成 Provider

通过 dashscope.MultiModalConversation SDK 调用 Qwen-Image 系列模型。
支持文生图（T2I）和图生图（I2I）。

官方文档：https://help.aliyun.com/zh/model-studio/qwen-image-api
"""

import asyncio
import json
import logging
import time
from typing import Any

from app.ai.providers.base import ImageProvider
from app.ai.schemas import (
    ImageProviderRequest,
    ImageProviderResponse,
    ImageResult,
)
from app.config import settings
from app.config.dashscope import get_image_size
from app.core.exceptions import AIServiceException

logger = logging.getLogger(__name__)


class QianwenProvider(ImageProvider):
    """阿里云千问（Qwen-Image）Provider"""

    def get_provider_id(self) -> str:
        return "qianwen"

    def is_available(self) -> bool:
        return bool(settings.dashscope.api_key.get_secret_value())

    async def generate_image(self, request: ImageProviderRequest) -> ImageProviderResponse:
        return await asyncio.to_thread(self._generate_sync, request)

    def _generate_sync(self, request: ImageProviderRequest) -> ImageProviderResponse:
        """通过 MultiModalConversation SDK 生成图像"""
        import dashscope
        from dashscope import MultiModalConversation

        api_key = settings.dashscope.api_key.get_secret_value()
        if not api_key:
            raise AIServiceException("DashScope API Key 未配置")

        # 模型名统一小写
        model = (request.model or settings.dashscope.model_image).lower()
        size = request.options.size or get_image_size(request.options.ratio)
        n = request.options.num_results

        # 设置 base URL
        # 如果配置了 Workspace ID，使用专属端点；否则使用共享 DashScope 端点
        if settings.dashscope.workspace_id:
            # 专属端点：{WorkspaceId}.cn-beijing.maas.aliyuncs.com
            dashscope.base_http_api_url = (
                f"https://{settings.dashscope.workspace_id}."
                f"{settings.dashscope.region}.maas.aliyuncs.com/api/v1"
            )
        else:
            # 共享端点
            dashscope.base_http_api_url = (
                f"https://dashscope.aliyuncs.com/api/v1"
            )

        logger.info("DashScope base_url: %s", dashscope.base_http_api_url)

        # 构建提示词
        prompt = request.prompt

        # 构建消息内容
        content: list[dict[str, Any]] = []

        # 如果有参考图，先加图片（图生图）
        if request.image_url:
            content.append({"image": request.image_url})

        # 加文本提示词
        content.append({"text": prompt})

        messages = [{"role": "user", "content": content}]

        logger.info(
            "[千问图像生成] 调用参数: model=%s, size=%s, n=%s, has_image=%s, prompt=%s",
            model, size, n, bool(request.image_url), prompt[:200],
        )
        logger.debug("[千问图像生成] 完整 messages: %s", json.dumps(messages, ensure_ascii=False, default=str))

        start_time = time.time()

        try:
            response = MultiModalConversation.call(
                api_key=api_key,
                model=model,
                messages=messages,
                prompt_extend=True,
            )
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error(
                "[千问图像生成] 调用异常 (耗时 %.1fs): %s", elapsed, exc,
            )
            logger.exception("MultiModalConversation 调用异常")
            raise AIServiceException(f"千问图像生成调用异常: {exc}") from exc

        elapsed = time.time() - start_time
        logger.info(
            "[千问图像生成] 调用完成: status_code=%s, 耗时=%.1fs",
            getattr(response, "status_code", None), elapsed,
        )
        logger.debug("[千问图像生成] 原始响应: %s", self._safe_dict(response))

        return self._parse_response(response, n)

    def _parse_response(self, response: Any, n: int) -> ImageProviderResponse:
        """解析 MultiModalConversation 响应"""
        status_code = getattr(response, "status_code", 0)

        if status_code != 200:
            code = getattr(response, "code", "")
            message = getattr(response, "message", str(response))
            raise AIServiceException(
                f"千问图像生成失败: HTTP {status_code} - code={code} message={message}"
            )

        # 从 choices[0].message.content 中提取图片 URL
        output = getattr(response, "output", None)
        if not output:
            raise AIServiceException("千问图像生成未返回 output")

        choices = self._get_attr(output, "choices") or []
        if not choices:
            raise AIServiceException("千问图像生成未返回 choices")

        results: list[ImageResult] = []
        for choice in choices[:n]:
            message = self._get_attr(choice, "message") or {}
            content = self._get_attr(message, "content") or []
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "image" in item:
                        url = item["image"]
                        if url:
                            results.append(
                                ImageResult(
                                    url=url,
                                    thumbnail_url=None,
                                    width=None,
                                    height=None,
                                    metadata={"raw_choice": self._safe_dict(choice)},
                                )
                            )

        if not results:
            logger.error("[千问图像生成] 解析失败: 未返回有效图片 URL")
            raise AIServiceException(
                f"千问图像生成未返回有效图片: raw={self._safe_dict(output)[:500]}"
            )

        result_urls = [r.url for r in results]
        logger.info(
            "[千问图像生成] 解析成功: 共 %d 张图片, URLs=%s",
            len(results), result_urls,
        )

        return ImageProviderResponse(
            status="success",
            results=results,
            provider_task_id=None,
            raw_response=self._safe_dict(output),
            error=None,
        )

    @staticmethod
    def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
        """兼容属性访问与字典访问"""
        if obj is None:
            return default
        if hasattr(obj, key):
            return getattr(obj, key)
        if isinstance(obj, dict):
            return obj.get(key, default)
        return default

    @classmethod
    def _safe_dict(cls, obj: Any) -> Any:
        """安全转为可序列化结构"""
        if obj is None:
            return None
        if isinstance(obj, (dict, list, str, int, float, bool)):
            return obj
        if hasattr(obj, "to_dict"):
            try:
                return obj.to_dict()
            except Exception:
                pass
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return str(obj)
