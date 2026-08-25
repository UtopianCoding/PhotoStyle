"""
OpenAI GPT Image 2 图像生成 Provider

通过 HTTP API 调用 GPT Image 2 模型。
支持文生图（T2I）、图生图（I2I）和图像编辑。

配置从内存缓存读取（数据库持久化），运行时修改立即生效。

官方文档：https://platform.openai.com/docs/api-reference/images
"""

import asyncio
import base64
import logging
import time
import uuid
from datetime import datetime
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

# HTTP 请求超时（秒）- GPT Image 2 是长任务，需要更长的超时
_REQUEST_TIMEOUT = 300.0


class DalleProvider(ImageProvider):
    """OpenAI GPT Image 2 图像生成 Provider"""

    def get_provider_id(self) -> str:
        return "dalle"

    def _get_config(self) -> dict[str, Any]:
        return model_config_store.get_config("dalle") or {}

    def is_available(self) -> bool:
        cfg = self._get_config()
        return bool(cfg.get("api_key"))

    async def generate_image(self, request: ImageProviderRequest) -> ImageProviderResponse:
        """
        生成图像。
        
        如果提供了 image_url 或 reference_images，使用图像编辑端点（/v1/images/edits）；
        否则使用图像生成端点（/v1/images/generations）。
        """
        cfg = self._get_config()
        api_key = cfg.get("api_key", "")
        if not api_key:
            raise AIServiceException("GPT Image 2 API Key 未配置")

        base_url = cfg.get("base_url", "https://api-direct.boft.ai/v1")
        # 清洗 URL：去除反引号、空白
        base_url = base_url.strip().strip("`").strip().rstrip("/")
        # 如果用户误填了完整路径，截断避免重复
        for suffix in ["/images/generations", "/images/edits"]:
            if base_url.endswith(suffix):
                base_url = base_url[: -len(suffix)]
                break
        
        model = (request.model or cfg.get("model_image", "gpt-image-2")).strip()
        prompt = request.prompt
        
        # 判断是否需要使用图像编辑端点
        has_input_image = bool(request.image_url or request.reference_images)
        
        if has_input_image:
            return await self._generate_with_image_edit(cfg, request, api_key, base_url, model, prompt)
        else:
            return await self._generate_text_to_image(cfg, request, api_key, base_url, model, prompt)

    async def _generate_text_to_image(
        self,
        cfg: dict[str, Any],
        request: ImageProviderRequest,
        api_key: str,
        base_url: str,
        model: str,
        prompt: str,
    ) -> ImageProviderResponse:
        """文本生成图像（/v1/images/generations）- 返回 base64 格式并上传到存储"""
        # 尺寸处理
        size = request.options.size or cfg.get("size", "auto")
        # 分辨率档位（仅在 size 为比例格式时生效）
        resolution = cfg.get("resolution", "1K")
        # 质量档位
        quality = cfg.get("quality", "medium")
        # 生成数量
        n = request.options.num_results
        
        # 构建请求体
        body: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "resolution": resolution,
            "quality": quality,
            "n": n,
            "response_format": "b64_json",  # 返回 base64 格式，避免临时 URL 过期问题
        }
        
        # 可选参数
        if cfg.get("background"):
            body["background"] = cfg["background"]
        if cfg.get("output_format"):
            body["output_format"] = cfg["output_format"]
        if cfg.get("output_compression") is not None:
            body["output_compression"] = int(cfg["output_compression"])
        if cfg.get("moderation"):
            body["moderation"] = cfg["moderation"]

        logger.info(
            "[GPT Image 2] 文生图调用: model=%s, size=%s, resolution=%s, quality=%s, n=%d, prompt=%s",
            model, size, resolution, quality, n, prompt[:200],
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
            logger.error("[GPT Image 2] 请求超时 (耗时 %.1fs)", elapsed)
            raise AIServiceException(f"GPT Image 2 请求超时: {exc}") from exc
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("[GPT Image 2] 请求异常 (耗时 %.1fs): %s", elapsed, exc)
            raise AIServiceException(f"GPT Image 2 请求异常: {exc}") from exc

        elapsed = time.time() - start_time
        logger.info(
            "[GPT Image 2] 文生图响应: status=%s, 耗时=%.1fs",
            response.status_code, elapsed,
        )

        return self._parse_response(response)

    async def _generate_with_image_edit(
        self,
        cfg: dict[str, Any],
        request: ImageProviderRequest,
        api_key: str,
        base_url: str,
        model: str,
        prompt: str,
    ) -> ImageProviderResponse:
        """图像编辑（/v1/images/edits），需要下载输入图片后以 multipart/form-data 上传
        
        请求格式：multipart/form-data
        - image: 图片文件（字段名必须为 "image"，多张图时重复使用该字段名）
        - model, prompt, size, resolution, quality, n, response_format 等表单字段
        
        参考格式（Python requests）：
            files=[('image', ('file.jpg', open('file.jpg','rb'), 'image/jpeg'))]
            data={'model': 'gpt-image-2', 'prompt': '...', ...}
        """
        # 尺寸处理
        size = request.options.size or cfg.get("size", "auto")
        resolution = cfg.get("resolution", "1K")
        quality = cfg.get("quality", "medium")
        n = request.options.num_results

        # 收集所有输入图片（主图 + 参考图）
        image_urls = []
        if request.image_url:
            image_urls.append(request.image_url)
        if request.reference_images:
            image_urls.extend(request.reference_images)

        if not image_urls:
            raise AIServiceException("图像编辑需要至少提供一张输入图片")

        logger.info(
            "[GPT Image 2] 图像编辑调用: model=%s, size=%s, resolution=%s, quality=%s, n=%d, images=%d, prompt=%s",
            model, size, resolution, quality, n, len(image_urls), prompt[:200],
        )

        # 下载所有输入图片并检测 Content-Type
        downloaded_images: list[tuple[str, bytes, str]] = []  # [(filename, content, content_type)]
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                for i, img_url in enumerate(image_urls):
                    logger.debug("[GPT Image 2] 下载输入图片 %d/%d: %s", i + 1, len(image_urls), img_url[:100])
                    resp = await client.get(img_url)
                    resp.raise_for_status()
                    # 从响应头获取真实 Content-Type，默认 image/jpeg
                    content_type = resp.headers.get("content-type", "image/jpeg")
                    # 清理 Content-Type（可能包含 charset 等参数）
                    content_type = content_type.split(";")[0].strip()
                    # 根据 Content-Type 推断文件扩展名
                    ext_map = {
                        "image/jpeg": ".jpg",
                        "image/png": ".png",
                        "image/webp": ".webp",
                        "image/gif": ".gif",
                    }
                    ext = ext_map.get(content_type, ".jpg")
                    filename = f"image_{i}{ext}"
                    downloaded_images.append((filename, resp.content, content_type))
                    logger.debug("[GPT Image 2] 图片 %d 下载完成: %d bytes, type=%s", i + 1, len(resp.content), content_type)
        except Exception as exc:
            logger.error("[GPT Image 2] 下载输入图片失败: %s", exc)
            raise AIServiceException(f"下载输入图片失败: {exc}") from exc

        # 构建 multipart/form-data
        # 关键：所有图片都使用 "image" 作为字段名（与 OpenAI API 规范一致）
        files: list[tuple[str, tuple[str, bytes, str]]] = []
        for filename, content, content_type in downloaded_images:
            files.append(("image", (filename, content, content_type)))

        # 其他表单字段（作为普通 form field，不是 JSON body）
        form_data: dict[str, str] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "resolution": resolution,
            "quality": quality,
            "n": str(n),
            "response_format": "b64_json",  # 返回 base64 格式，避免临时 URL 过期问题
        }
        
        # 可选参数（仅在明确设置时传入）
        if cfg.get("background"):
            form_data["background"] = cfg["background"]
        if cfg.get("output_format"):
            form_data["output_format"] = cfg["output_format"]
        if cfg.get("output_compression") is not None:
            form_data["output_compression"] = str(int(cfg["output_compression"]))
        if cfg.get("moderation"):
            form_data["moderation"] = cfg["moderation"]

        # 注意：不要手动设置 Content-Type，httpx 会自动添加 multipart/form-data + boundary
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        url = f"{base_url}/images/edits"
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                response = await client.post(url, data=form_data, files=files, headers=headers)
        except httpx.TimeoutException as exc:
            elapsed = time.time() - start_time
            logger.error("[GPT Image 2] 图像编辑请求超时 (耗时 %.1fs)", elapsed)
            raise AIServiceException(f"GPT Image 2 图像编辑请求超时: {exc}") from exc
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("[GPT Image 2] 图像编辑请求异常 (耗时 %.1fs): %s", elapsed, exc)
            raise AIServiceException(f"GPT Image 2 图像编辑请求异常: {exc}") from exc

        elapsed = time.time() - start_time
        logger.info(
            "[GPT Image 2] 图像编辑响应: status=%s, 耗时=%.1fs",
            response.status_code, elapsed,
        )

        return self._parse_response(response)

    async def _parse_response(self, response: httpx.Response) -> ImageProviderResponse:
        """解析 GPT Image 2 响应，支持 b64_json 和 url 两种格式"""
        if response.status_code != 200:
            error_text = response.text[:500]
            logger.error("[GPT Image 2] HTTP %s: %s", response.status_code, error_text)
            raise AIServiceException(
                f"GPT Image 2 失败: HTTP {response.status_code} - {error_text}"
            )

        try:
            data = response.json()
        except Exception as exc:
            raise AIServiceException(
                f"GPT Image 2 响应解析失败: {exc}"
            ) from exc

        # 响应格式：{"data": [{"url": "..."}, ...]} 或 {"data": [{"b64_json": "..."}, ...]}
        items = data.get("data")
        if not items:
            logger.error("[GPT Image 2] 响应无 data: %s", str(data)[:500])
            raise AIServiceException(
                f"GPT Image 2 未返回有效数据: {str(data)[:500]}"
            )

        results: list[ImageResult] = []
        for i, item in enumerate(items):
            url = item.get("url")
            b64_json = item.get("b64_json")
            
            if b64_json:
                # base64 格式：解码并上传到存储
                try:
                    image_bytes = base64.b64decode(b64_json)
                    logger.info("[GPT Image 2] 解码 base64: %d bytes", len(image_bytes))
                    
                    # 上传到存储
                    from app.core.storage import get_storage_provider
                    
                    storage = get_storage_provider()
                    date = datetime.utcnow().strftime("%Y%m%d")
                    ext = "png"  # GPT Image 2 默认返回 PNG
                    key = f"results/gpt-image-2/{date}/{uuid.uuid4().hex}.{ext}"
                    url = await asyncio.to_thread(
                        storage.upload, key, image_bytes, "image/png"
                    )
                    logger.info("[GPT Image 2] 上传到存储: %s", url)
                except Exception as exc:
                    logger.error("[GPT Image 2] base64 上传失败: %s", exc)
                    raise AIServiceException(f"GPT Image 2 base64 上传失败: {exc}") from exc
            elif url:
                # URL 格式：直接使用
                logger.info("[GPT Image 2] 使用临时 URL 格式")
            else:
                # 既没有 url 也没有 b64_json
                logger.warning("[GPT Image 2] 跳过无效项 %d: %s", i, str(item)[:200])
                continue
            
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
                f"GPT Image 2 未返回有效图片: {str(data)[:500]}"
            )

        result_urls = [r.url for r in results]
        logger.info(
            "[GPT Image 2] 解析成功: 共 %d 张图片, URLs=%s",
            len(results), result_urls,
        )

        return ImageProviderResponse(
            status="success",
            results=results,
            provider_task_id=None,
            raw_response=data,
            error=None,
        )
