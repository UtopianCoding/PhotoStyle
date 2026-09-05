"""
Gemini（Nano Banana Pro / Google Gemini 图像模型）图像生成 Provider

通过 Gemini 原生 generateContent 接口调用图像生成模型
（如 gemini-3-pro-image-preview / gemini-2.5-flash-image），
支持文生图、图生图与图像编辑。

接口说明（兼容官方 Gemini API 与各类中转网关）：
    POST {base_url}/v1beta/models/{model}:generateContent
    Authorization: Bearer {api_key}

同步响应在 candidates[].content.parts[] 中返回文本或 Base64 图片
（inlineData.data），本 Provider 会解码 base64 并上传到对象存储。

配置从内存缓存读取（数据库持久化），运行时修改立即生效。
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

# HTTP 请求超时（秒）
_REQUEST_TIMEOUT = 300.0

# 默认官方端点
_DEFAULT_BASE_URL = "https://api-direct.boft.ai"
# 默认模型（Nano Banana Pro）
_DEFAULT_MODEL = "gemini-3-pro-image-preview"

# 支持的比例枚举（Gemini imageConfig.aspectRatio）
_SUPPORTED_ASPECT_RATIOS = [
    "1:1", "3:2", "2:3", "3:4", "4:3",
    "4:5", "5:4", "9:16", "16:9", "21:9",
]


def _normalize_aspect_ratio(value: str | None) -> str | None:
    """将各种比例写法规范化为 Gemini 支持的比例（如 3:4、2:3、16:9）"""
    if not value:
        return None
    v = str(value).strip().lower()
    # 支持 "1024x768" / "768*1024" 像素写法 → 转为比例
    import re
    m = re.fullmatch(r"(\d+)\s*[xX*×]\s*(\d+)", v)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        gcd = __import__("math").gcd(w, h)
        w, h = w // gcd, h // gcd
        # 缩小到常见比例范围内（避免超大整数比）
        while max(w, h) > 16 and w % 2 == 0 and h % 2 == 0:
            w //= 2
            h //= 2
        v = f"{w}:{h}"
    # 规范化空格：如 " 1 : 1 " -> "1:1"
    parts = v.replace("：", ":").split(":")
    if len(parts) == 2:
        v = f"{parts[0].strip()}:{parts[1].strip()}"
    # 若不在枚举中，尝试翻转或取近似（无法识别则返回 None 交给后端默认）
    if v in _SUPPORTED_ASPECT_RATIOS:
        return v
    # 常见反斜杠/中文冒号容错已在上面处理；这里丢弃无法识别的
    logger.warning("[Gemini图像生成] 无法识别的比例 %r，使用默认", value)
    return None


class GeminiProvider(ImageProvider):
    """Gemini 图像生成 Provider（原生 generateContent）"""

    def get_provider_id(self) -> str:
        return "gemini"

    def _get_config(self) -> dict[str, Any]:
        return model_config_store.get_config("gemini") or {}

    def is_available(self) -> bool:
        return bool(self._get_config().get("api_key"))

    async def generate_image(self, request: ImageProviderRequest) -> ImageProviderResponse:
        """
        通过 Gemini generateContent 生成图像。

        - 无输入图片：文生图（parts 仅含 text）；
        - 提供 image_url / reference_images：图生图/编辑（parts 内嵌 base64 图片）。
        """
        cfg = self._get_config()
        api_key = cfg.get("api_key", "")
        if not api_key:
            raise AIServiceException("Gemini API Key 未配置")

        base_url = cfg.get("base_url", _DEFAULT_BASE_URL)
        # 清洗 URL：去除反引号、空白、尾部重复路径
        base_url = base_url.strip().strip("`").strip().rstrip("/")
        # 若误填了完整 v1beta/models/xxx 路径，截断到根
        for marker in ("/v1beta/models", "/v1/models", "/generateContent"):
            idx = base_url.find(marker)
            if idx != -1:
                base_url = base_url[:idx]
                break

        model = (request.model or cfg.get("model_image", _DEFAULT_MODEL)).strip()
        prompt = request.prompt

        # 组装 parts：有输入图时先放图（base64 inline_data），再放提示词
        parts: list[dict[str, Any]] = []
        image_urls: list[str] = []
        if request.image_url:
            image_urls.append(request.image_url)
        if request.reference_images:
            image_urls.extend(request.reference_images)

        if image_urls:
            # 下载全部输入图片 → base64 inlineData（Boft/OpenAI 兼容网关使用 camelCase）
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    for i, img_url in enumerate(image_urls):
                        logger.debug(
                            "[Gemini图像生成] 下载输入图片 %d/%d: %s",
                            i + 1, len(image_urls), img_url[:100],
                        )
                        resp = await client.get(img_url)
                        resp.raise_for_status()
                        mime = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                        if not mime.startswith("image/"):
                            mime = "image/jpeg"
                        b64 = base64.b64encode(resp.content).decode("ascii")
                        parts.append(
                            {"inlineData": {"mimeType": mime, "data": b64}}
                        )
            except Exception as exc:
                logger.error("[Gemini图像生成] 下载输入图片失败: %s", exc)
                raise AIServiceException(f"下载输入图片失败: {exc}") from exc

            # 图生图提示词：说明输入图片角色（主图为内容源，参考图为风格）
            if request.image_url and request.reference_images:
                prompt = (
                    "The FIRST image is the CONTENT SOURCE - preserve ALL content "
                    "elements from it (people, animals, poses, clothing, composition). "
                    "The following image(s) are STYLE REFERENCES ONLY - apply their "
                    "drawing style but never copy their subjects.\n\n" + prompt
                )
            elif request.reference_images:
                prompt = (
                    "The attached image is a STYLE REFERENCE. Apply its artistic style "
                    "to the requested scene.\n\n" + prompt
                )

        parts.append({"text": prompt})

        # generationConfig：图像输出配置（Gemini REST 用 camelCase）
        generation_config: dict[str, Any] = {
            "responseModalities": ["IMAGE"],
        }
        image_config = self._build_image_config(cfg, request)
        if image_config:
            generation_config["imageConfig"] = image_config

        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": generation_config,
        }

        logger.info(
            "[Gemini图像生成] 调用参数: model=%s, parts=%d(图%d+文1), imageConfig=%s, prompt=%s",
            model, len(parts), len(image_urls), image_config, prompt[:200],
        )
        masked_key = f"{api_key[:8]}****{api_key[-4:]}" if api_key else "(未配置)"
        logger.debug(
            "[Gemini图像生成] 请求详情: url=%s/v1beta/models/%s:generateContent, api_key=%s, body=%s",
            base_url, model, masked_key, _safe_truncate(body),
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        url = f"{base_url}/v1beta/models/{model}:generateContent"
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                response = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            logger.error("[Gemini图像生成] 请求超时 (耗时 %.1fs)", time.time() - start_time)
            raise AIServiceException(f"Gemini 图像生成请求超时: {exc}") from exc
        except Exception as exc:
            logger.error("[Gemini图像生成] 请求异常 (耗时 %.1fs): %s", time.time() - start_time, exc)
            raise AIServiceException(f"Gemini 图像生成请求异常: {exc}") from exc

        logger.info(
            "[Gemini图像生成] 响应: status=%s, 耗时=%.1fs",
            response.status_code, time.time() - start_time,
        )

        return await self._parse_response(response)

    # -------------------- 图像配置 --------------------

    def _build_image_config(
        self, cfg: dict[str, Any], request: ImageProviderRequest
    ) -> dict[str, str] | None:
        """
        构建 imageConfig（aspectRatio + imageSize）。

        比例来源优先级：
        1. cfg.aspect_ratio（后台配置，如 3:4）；
        2. cfg.resolution 解析出的宽高比（如 768*1024 → 3:4）；
        3. cfg.width/height 的宽高比；
        4. request.options.ratio（技能声明比例，如 2:3）。

        尺寸档位来源：
        1. cfg.image_size（如 1K/2K/4K）；
        2. cfg.resolution / width/height 解析出的长边自动映射。
        """
        from app.ai.dashscope_utils import parse_resolution

        aspect_ratio: str | None = None
        cfg_ar = (cfg.get("aspect_ratio") or "").strip()
        if cfg_ar:
            aspect_ratio = _normalize_aspect_ratio(cfg_ar)

        # 分辨率/宽高推导
        parsed = parse_resolution(cfg.get("resolution"))
        width = cfg.get("width")
        height = cfg.get("height")
        long_edge: int | None = None
        if parsed:
            long_edge = max(parsed)
            if not aspect_ratio:
                aspect_ratio = _normalize_aspect_ratio(f"{parsed[0]}x{parsed[1]}")
        elif width and height:
            long_edge = max(int(width), int(height))
            if not aspect_ratio:
                aspect_ratio = _normalize_aspect_ratio(f"{int(width)}x{int(height)}")

        # 请求选项比例
        if not aspect_ratio:
            ratio = (request.options.ratio or "").strip() or (
                (request.options.size or "").strip()
            )
            aspect_ratio = _normalize_aspect_ratio(ratio)

        # 尺寸档位
        image_size: str | None = None
        cfg_is = (cfg.get("image_size") or "").strip().upper()
        if cfg_is in ("1K", "2K", "4K"):
            image_size = cfg_is
        elif long_edge:
            if long_edge <= 1100:
                image_size = "1K"
            elif long_edge <= 2200:
                image_size = "2K"
            else:
                image_size = "4K"

        image_config: dict[str, str] = {}
        if aspect_ratio:
            image_config["aspectRatio"] = aspect_ratio
        if image_size:
            image_config["imageSize"] = image_size
        return image_config or None

    # -------------------- 响应解析 --------------------

    async def _parse_response(self, response: httpx.Response) -> ImageProviderResponse:
        """解析 generateContent 响应：candidates[].content.parts[] 内提取 base64 图片"""
        if response.status_code != 200:
            error_text = response.text[:800]
            logger.error("[Gemini图像生成] HTTP %s: %s", response.status_code, error_text)
            # 尝试提取错误消息
            try:
                data = response.json()
                msg = (
                    data.get("error", {}).get("message")
                    if isinstance(data.get("error"), dict)
                    else data.get("message")
                )
                if msg:
                    raise AIServiceException(f"Gemini 图像生成失败: {msg}")
            except AIServiceException:
                raise
            except Exception:
                pass
            raise AIServiceException(
                f"Gemini 图像生成失败: HTTP {response.status_code} - {error_text}"
            )

        try:
            data = response.json()
        except Exception as exc:
            raise AIServiceException(f"Gemini 图像生成响应解析失败: {exc}") from exc

        # 提取所有图片 part
        image_b64_items: list[tuple[str, str]] = []  # [(mime_type, data)]
        candidates = data.get("candidates") or []
        for cand in candidates:
            content = cand.get("content") or {}
            parts = content.get("parts") or []
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if isinstance(inline, dict) and inline.get("data"):
                    image_b64_items.append(
                        (
                            inline.get("mimeType") or inline.get("mime_type") or "image/png",
                            inline["data"],
                        )
                    )

        if not image_b64_items:
            # 无图片：可能是文本说明或错误
            text_parts = []
            for cand in candidates:
                for part in (cand.get("content") or {}).get("parts") or []:
                    if part.get("text"):
                        text_parts.append(part["text"])
            logger.error(
                "[Gemini图像生成] 响应未包含图片: %s",
                str(data)[:800],
            )
            raise AIServiceException(
                f"Gemini 图像生成未返回图片: {(' '.join(text_parts))[:300] or str(data)[:300]}"
            )

        results: list[ImageResult] = []
        storage = None
        from app.core.storage import get_storage_provider

        storage = get_storage_provider()
        date = datetime.utcnow().strftime("%Y%m%d")
        for mime_type, b64_data in image_b64_items:
            try:
                image_bytes = base64.b64decode(b64_data)
            except Exception as exc:
                logger.warning("[Gemini图像生成] base64 解码失败: %s", exc)
                continue
            # 上传到存储
            ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
            ext = ext_map.get(mime_type.lower(), ".png")
            content_type = mime_type if mime_type.startswith("image/") else "image/png"
            key = f"results/gemini/{date}/{uuid.uuid4().hex}{ext}"
            try:
                url = await asyncio.to_thread(
                    storage.upload, key, image_bytes, content_type
                )
            except Exception as exc:
                logger.error("[Gemini图像生成] 图片上传失败: %s", exc)
                raise AIServiceException(f"Gemini 图像上传失败: {exc}") from exc
            results.append(
                ImageResult(
                    url=url,
                    thumbnail_url=None,
                    width=None,
                    height=None,
                    metadata={"mime_type": mime_type},
                )
            )

        if not results:
            raise AIServiceException(
                f"Gemini 图像生成未返回有效图片: {str(data)[:500]}"
            )

        result_urls = [r.url for r in results]
        logger.info("[Gemini图像生成] 解析成功: 共 %d 张图片, URLs=%s", len(results), result_urls)

        return ImageProviderResponse(
            status="success",
            results=results,
            provider_task_id=None,
            raw_response=_strip_base64(data),
            error=None,
        )


def _safe_truncate(obj: Any, limit: int = 2000) -> str:
    """安全转 JSON 并截断（避免把 base64 图片全量打进日志）"""
    import json

    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return str(obj)[:limit]
    return s[:limit]


def _strip_base64(data: Any) -> Any:
    """清理 raw_response 中的 base64 大字段，避免数据库过大"""
    import json

    def _clean(o: Any) -> Any:
        if isinstance(o, dict):
            return {
                k: _clean(v)
                for k, v in o.items()
                if k != "data"
                or not isinstance(v, str)
                or len(v) < 64
            }
        if isinstance(o, list):
            return [_clean(i) for i in o]
        return o

    return _clean(data)
