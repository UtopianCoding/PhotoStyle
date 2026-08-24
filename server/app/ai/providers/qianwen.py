"""
阿里云千问（Qwen-Image）图像生成 Provider

通过 dashscope.MultiModalConversation SDK 调用 Qwen-Image 系列模型。
支持文生图（T2I）和图生图（I2I）。

配置从内存缓存读取（数据库持久化），运行时修改立即生效。

官方文档：https://help.aliyun.com/zh/model-studio/qwen-image-api
"""

import json
import logging
import time
from typing import Any

from app.ai.providers.base import ImageProvider
from app.ai.dashscope_utils import run_blocking_with_timeout
from app.ai.schemas import (
    ImageProviderRequest,
    ImageProviderResponse,
    ImageResult,
)
from app.config.dashscope import get_image_size
from app.core.exceptions import AIServiceException
from app.services.model_config_store import model_config_store

logger = logging.getLogger(__name__)


class QianwenProvider(ImageProvider):
    """阿里云千问（Qwen-Image）Provider"""

    def get_provider_id(self) -> str:
        return "qianwen"

    def _get_config(self) -> dict[str, Any]:
        return model_config_store.get_config("qianwen") or {}

    def is_available(self) -> bool:
        return bool(self._get_config().get("api_key"))

    async def generate_image(self, request: ImageProviderRequest) -> ImageProviderResponse:
        # 同步 SDK 放入线程池执行，并加超时（retries=1：硬失败不重复放大延迟）
        return await run_blocking_with_timeout(
            self._generate_sync,
            request,
            timeout=120.0,
            retries=1,
            label="千问图像生成",
        )

    def _generate_sync(self, request: ImageProviderRequest) -> ImageProviderResponse:
        """通过 MultiModalConversation SDK 生成图像"""
        import dashscope
        from dashscope import MultiModalConversation

        cfg = self._get_config()
        api_key = cfg.get("api_key", "")
        if not api_key:
            raise AIServiceException("DashScope API Key 未配置")

        # 模型名统一小写
        model = (request.model or cfg.get("model_image", "qwen-image-3.0-pro")).lower()
        # 尺寸优先级：配置 width/height > options.size > ratio 默认映射
        cfg_width = cfg.get("width")
        cfg_height = cfg.get("height")
        if cfg_width and cfg_height:
            size = f"{cfg_width}*{cfg_height}"
        else:
            size = request.options.size or get_image_size(request.options.ratio)
        n = request.options.num_results
        workspace_id = cfg.get("workspace_id", "")
        region = cfg.get("region", "cn-beijing")
        # 可选参数：水印、种子（为空则不传）
        cfg_watermark = cfg.get("watermark")
        cfg_seed = cfg.get("seed")

        # 设置 base URL
        # 如果配置了 Workspace ID，使用专属端点；否则使用共享 DashScope 端点
        if workspace_id:
            dashscope.base_http_api_url = (
                f"https://{workspace_id}.{region}.maas.aliyuncs.com/api/v1"
            )
        else:
            dashscope.base_http_api_url = (
                f"https://dashscope.aliyuncs.com/api/v1"
            )

        logger.info("DashScope base_url: %s", dashscope.base_http_api_url)

        # 构建提示词
        prompt = request.prompt

        # 构建消息内容
        content: list[dict[str, Any]] = []

        # 添加图片：用户内容图在前，风格参考图在后
        if request.image_url:
            content.append({"image": request.image_url})
        if request.reference_images:
            for ref_img in request.reference_images:
                content.append({"image": ref_img})

        # 如果有参考图，在提示词开头注入角色说明
        if request.reference_images:
            prompt = (
                "I provided two images. "
                "The FIRST image is the CONTENT SOURCE - preserve ALL content elements from it: people, animals, poses, actions, clothing, accessories, and interactive objects. "
                "The SECOND image is the STYLE REFERENCE ONLY - copy its drawing style (rough outlines, flat color blocks, chibi proportions, signature) but NEVER copy any person, object, text, or signature from it. "
                "\n\n" + prompt
            )

        content.append({"text": prompt})

        messages = [{"role": "user", "content": content}]

        logger.info(
            "[千问图像生成] 调用参数: model=%s, size=%s, n=%s, watermark=%s, seed=%s, has_image=%s, ref_images=%d, prompt=%s",
            model, size, n, cfg_watermark, cfg_seed, bool(request.image_url), len(request.reference_images), prompt[:200],
        )
        logger.debug("[千问图像生成] 完整 messages: %s", json.dumps(messages, ensure_ascii=False, default=str))

        start_time = time.time()

        try:
            # 构建额外参数（仅在有值时传入）
            extra_kwargs: dict[str, Any] = {
                "prompt_extend": True,  # 启用提示词自动扩展，让模型优化生成效果
                "size": size,
            }
            if cfg_watermark is not None:
                extra_kwargs["watermark"] = bool(cfg_watermark)
            if cfg_seed is not None:
                extra_kwargs["seed"] = int(cfg_seed)

            response = MultiModalConversation.call(
                api_key=api_key,
                model=model,
                messages=messages,
                **extra_kwargs,
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
