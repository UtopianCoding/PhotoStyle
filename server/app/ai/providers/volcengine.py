"""
火山引擎（Seedream）图像生成 Provider

通过 HTTP API 调用火山引擎 Seedream 系列图像生成模型。
支持文生图（T2I）和图生图（I2I）。

配置从内存缓存读取（数据库持久化），运行时修改立即生效。

官方文档：https://console.volcengine.com/ark/region:cn-beijing/docs/82379/1541523
"""

import logging
import time
from typing import Any

import httpx

from app.ai.providers.base import ImageProvider
from app.ai.schemas import (
    ImageProviderRequest,
    ImageProviderResponse,
    ImageResult,
)
from app.core.exceptions import AIServiceException
from app.services.model_config_store import model_config_store

logger = logging.getLogger(__name__)

# HTTP 请求超时（秒）
_REQUEST_TIMEOUT = 120.0


class VolcengineProvider(ImageProvider):
    """火山引擎 Seedream 图像生成 Provider"""

    def get_provider_id(self) -> str:
        return "volcengine"

    def _get_config(self) -> dict[str, Any]:
        return model_config_store.get_config("volcengine") or {}

    def is_available(self) -> bool:
        return bool(self._get_config().get("api_key"))

    async def generate_image(self, request: ImageProviderRequest) -> ImageProviderResponse:
        cfg = self._get_config()
        api_key = cfg.get("api_key", "")
        if not api_key:
            raise AIServiceException("火山引擎 API Key 未配置")

        base_url = cfg.get("base_url", "https://ark.cn-beijing.volces.com/api/plan/v3")
        # 清洗 URL：去除反引号、空白
        base_url = base_url.strip().strip("`").strip().rstrip("/")
        # 如果用户误填了完整路径（含 /images/generations），截断避免重复
        if base_url.endswith("/images/generations"):
            base_url = base_url[: -len("/images/generations")]
        model = (request.model or cfg.get("model_image", "seedream-5-0-pro")).strip()
        prompt = request.prompt
        # 尺寸优先级：resolution（如 1024*1024）> width/height > options.size > 默认 2048x2048
        from app.ai.dashscope_utils import parse_resolution

        parsed = parse_resolution(cfg.get("resolution"))
        cfg_width = cfg.get("width")
        cfg_height = cfg.get("height")
        if parsed:
            size = f"{parsed[0]}x{parsed[1]}"
        elif cfg_width and cfg_height:
            size = f"{int(cfg_width)}x{int(cfg_height)}"
        else:
            size = request.options.size or "2048x2048"
        # 可选参数：水印、种子（为空则不传）
        cfg_watermark = cfg.get("watermark")
        cfg_seed = cfg.get("seed")

        # 构建请求体
        body: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
        }
        # 水印：仅在明确设置时传入
        if cfg_watermark is not None:
            body["watermark"] = bool(cfg_watermark)
        # 随机种子：仅在明确设置时传入
        if cfg_seed is not None:
            body["seed"] = int(cfg_seed)

        # 图生图：添加参考图片
        if request.image_url:
            body["image"] = request.image_url
        elif request.reference_images:
            # 多图场景传入列表
            body["image"] = request.reference_images

        if request.reference_images and request.image_url:
            # 同时有主图和参考图时，合并为列表（主图在前）
            body["image"] = [request.image_url] + request.reference_images

        logger.info(
            "[火山引擎图像生成] 调用参数: model=%s, size=%s, watermark=%s, seed=%s, has_image=%s, ref_images=%d, prompt=%s",
            model, size, cfg_watermark, cfg_seed, bool(request.image_url), len(request.reference_images), prompt[:200],
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{base_url}/images/generations"
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                response = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            elapsed = time.time() - start_time
            logger.error("[火山引擎图像生成] 请求超时 (耗时 %.1fs)", elapsed)
            raise AIServiceException(f"火山引擎图像生成请求超时: {exc}") from exc
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("[火山引擎图像生成] 请求异常 (耗时 %.1fs): %s", elapsed, exc)
            raise AIServiceException(f"火山引擎图像生成请求异常: {exc}") from exc

        elapsed = time.time() - start_time
        logger.info(
            "[火山引擎图像生成] 响应: status=%s, 耗时=%.1fs",
            response.status_code, elapsed,
        )

        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: httpx.Response) -> ImageProviderResponse:
        """解析火山引擎 images/generations 响应"""
        if response.status_code != 200:
            error_text = response.text[:500]
            logger.error("[火山引擎图像生成] HTTP %s: %s", response.status_code, error_text)
            raise AIServiceException(
                f"火山引擎图像生成失败: HTTP {response.status_code} - {error_text}"
            )

        try:
            data = response.json()
        except Exception as exc:
            raise AIServiceException(
                f"火山引擎图像生成响应解析失败: {exc}"
            ) from exc

        # 响应格式：{"data": [{"url": "..."}, ...]} 或 {"data": [{"b64_json": "..."}, ...]}
        items = data.get("data")
        if not items:
            logger.error("[火山引擎图像生成] 响应无 data: %s", str(data)[:500])
            raise AIServiceException(
                f"火山引擎图像生成未返回有效数据: {str(data)[:500]}"
            )

        results: list[ImageResult] = []
        for item in items:
            url = item.get("url")
            if url:
                results.append(
                    ImageResult(
                        url=url,
                        thumbnail_url=None,
                        width=None,
                        height=None,
                        metadata=item,
                    )
                )

        if not results:
            raise AIServiceException(
                f"火山引擎图像生成未返回有效图片 URL: {str(data)[:500]}"
            )

        result_urls = [r.url for r in results]
        logger.info(
            "[火山引擎图像生成] 解析成功: 共 %d 张图片, URLs=%s",
            len(results), result_urls,
        )

        return ImageProviderResponse(
            status="success",
            results=results,
            provider_task_id=None,
            raw_response=data,
            error=None,
        )
