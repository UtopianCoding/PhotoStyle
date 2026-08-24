"""
MiniMax 图像生成 Provider

通过 HTTP API 调用 MiniMax image-01 / image-01-live 图像生成模型。
支持文生图（T2I）和图生图（I2I，通过 subject_reference 传入人像参考图）。

配置从内存缓存读取（数据库持久化），运行时修改立即生效。

官方文档：https://platform.minimaxi.com/docs/api-reference/image-generation-i2i
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

# MiniMax 支持的宽高比映射（与 API 文档对齐）
_VALID_ASPECT_RATIOS = {
    "1:1", "16:9", "4:3", "3:2", "2:3", "3:4", "9:16", "21:9",
}


class MinimaxProvider(ImageProvider):
    """MiniMax 图像生成 Provider"""

    def get_provider_id(self) -> str:
        return "minimax"

    def _get_config(self) -> dict[str, Any]:
        return model_config_store.get_config("minimax") or {}

    def is_available(self) -> bool:
        return bool(self._get_config().get("api_key"))

    async def generate_image(self, request: ImageProviderRequest) -> ImageProviderResponse:
        cfg = self._get_config()
        api_key = cfg.get("api_key", "")
        if not api_key:
            raise AIServiceException("MiniMax API Key 未配置")

        base_url = cfg.get("base_url", "https://api.minimaxi.com/v1")
        # 清洗 URL：去除反引号、空白、末尾斜杠
        base_url = base_url.strip().strip("`").strip().rstrip("/")
        # 如果用户误填了完整路径（含 /image_generation），截断避免重复
        if base_url.endswith("/image_generation"):
            base_url = base_url[: -len("/image_generation")]

        model = (request.model or cfg.get("model_image", "image-01")).strip()
        prompt = request.prompt
        # 水印开关：默认关闭
        watermark = cfg.get("watermark", False)

        # 构建请求体
        body: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "response_format": "url",
            "aigc_watermark": bool(watermark),
        }

        # 宽高比：从 options.ratio 映射（仅使用 MiniMax 支持的值）
        ratio = request.options.ratio or "1:1"
        if ratio in _VALID_ASPECT_RATIOS:
            body["aspect_ratio"] = ratio
        else:
            # 默认使用 1:1
            body["aspect_ratio"] = "1:1"

        # 生成数量
        n = request.options.num_results
        if n > 1:
            body["n"] = min(n, 9)  # MiniMax 最多 9 张

        # 图生图：通过 subject_reference 传入人像参考图
        if request.image_url:
            body["subject_reference"] = [
                {"type": "character", "image_file": request.image_url}
            ]
        elif request.reference_images:
            # 多图场景：将所有参考图作为人像参考
            body["subject_reference"] = [
                {"type": "character", "image_file": img}
                for img in request.reference_images
            ]

        logger.info(
            "[MiniMax图像生成] 调用参数: model=%s, aspect_ratio=%s, n=%s, "
            "has_image=%s, ref_images=%d, prompt=%s",
            model, body.get("aspect_ratio"), body.get("n", 1),
            bool(request.image_url), len(request.reference_images), prompt[:200],
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{base_url}/image_generation"
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                response = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            elapsed = time.time() - start_time
            logger.error("[MiniMax图像生成] 请求超时 (耗时 %.1fs)", elapsed)
            raise AIServiceException(f"MiniMax 图像生成请求超时: {exc}") from exc
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("[MiniMax图像生成] 请求异常 (耗时 %.1fs): %s", elapsed, exc)
            raise AIServiceException(f"MiniMax 图像生成请求异常: {exc}") from exc

        elapsed = time.time() - start_time
        logger.info(
            "[MiniMax图像生成] 响应: status=%s, 耗时=%.1fs",
            response.status_code, elapsed,
        )

        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: httpx.Response) -> ImageProviderResponse:
        """解析 MiniMax image_generation 响应"""
        if response.status_code != 200:
            error_text = response.text[:500]
            logger.error("[MiniMax图像生成] HTTP %s: %s", response.status_code, error_text)
            raise AIServiceException(
                f"MiniMax 图像生成失败: HTTP {response.status_code} - {error_text}"
            )

        try:
            data = response.json()
        except Exception as exc:
            raise AIServiceException(
                f"MiniMax 图像生成响应解析失败: {exc}"
            ) from exc

        # 检查业务状态码
        base_resp = data.get("base_resp", {})
        status_code = base_resp.get("status_code", -1)
        if status_code != 0:
            status_msg = base_resp.get("status_msg", "未知错误")
            logger.error("[MiniMax图像生成] 业务错误: code=%s, msg=%s", status_code, status_msg)
            raise AIServiceException(
                f"MiniMax 图像生成失败: code={status_code} - {status_msg}"
            )

        # 提取图片 URL 列表
        result_data = data.get("data", {})
        image_urls = result_data.get("image_urls", [])

        if not image_urls:
            logger.error("[MiniMax图像生成] 响应无有效图片: %s", str(data)[:500])
            raise AIServiceException(
                f"MiniMax 图像生成未返回有效图片: {str(data)[:500]}"
            )

        results: list[ImageResult] = []
        for url in image_urls:
            if url:
                results.append(
                    ImageResult(
                        url=url,
                        thumbnail_url=None,
                        width=None,
                        height=None,
                        metadata={},
                    )
                )

        # 提取任务元信息
        metadata_info = data.get("metadata", {})
        success_count = metadata_info.get("success_count", len(results))
        failed_count = metadata_info.get("failed_count", 0)

        result_urls = [r.url for r in results]
        logger.info(
            "[MiniMax图像生成] 解析成功: 共 %d 张图片, 成功=%d, 失败=%d, URLs=%s",
            len(results), success_count, failed_count, result_urls,
        )

        return ImageProviderResponse(
            status="success",
            results=results,
            provider_task_id=data.get("id"),
            raw_response=data,
            error=None,
        )
