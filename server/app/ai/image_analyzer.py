"""
图片分析器

使用 DashScope qwen-vl-plus 视觉理解模型分析图片内容，
输出结构化信息（主体、场景、情绪、构图、色调、关键物件），
用于增强风格转换提示词的相关性。

由于 dashscope SDK 为同步阻塞调用，这里通过 asyncio.to_thread
将其放入线程池执行。
"""

import asyncio
import json
import logging
import time
from typing import Any

from app.ai.schemas import ImageAnalysis
from app.config import settings
from app.config.dashscope import (
    EDITORIAL_ANALYSIS_SYSTEM_PROMPT,
    REVIVAL_ANALYSIS_SYSTEM_PROMPT,
    VISION_ANALYSIS_SYSTEM_PROMPT,
)
from app.core.exceptions import AIServiceException

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """图片内容分析器"""

    # 视觉理解模型默认名称
    DEFAULT_MODEL = settings.dashscope.model_vision

    def __init__(self, model: str | None = None) -> None:
        self.model = model or self.DEFAULT_MODEL

    async def analyze(self, image_url: str) -> ImageAnalysis:
        """
        分析图片内容，返回结构化结果。

        Args:
            image_url: 待分析的图片地址（需可被 DashScope 访问）

        Returns:
            ImageAnalysis 模式对象
        """
        return await asyncio.to_thread(self._analyze_sync, image_url)

    def _analyze_sync(self, image_url: str) -> ImageAnalysis:
        """同步执行视觉分析（在线程池中运行）"""
        from dashscope import MultiModalConversation
        from http import HTTPStatus

        api_key = settings.dashscope.api_key.get_secret_value()
        if not api_key:
            raise AIServiceException("DashScope API Key 未配置")

        # 组装多模态消息：系统提示 + 用户图片
        messages = [
            {
                "role": "system",
                "content": [{"text": VISION_ANALYSIS_SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [
                    {"image": image_url},
                    {"text": "请分析这张图片并按要求输出 JSON。"},
                ],
            },
        ]

        logger.info("[图片分析] 调用 qwen-vl-plus: image_url=%s", image_url)
        logger.debug("[图片分析] 完整 messages: %s", json.dumps(messages, ensure_ascii=False, default=str))

        start_time = time.time()

        try:
            rsp = MultiModalConversation.call(
                model=self.model,
                messages=messages,
                api_key=api_key,
            )
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("[图片分析] 调用异常 (耗时 %.1fs): %s", elapsed, exc)
            logger.exception("DashScope 视觉分析调用异常")
            raise AIServiceException(f"图片分析调用失败: {exc}") from exc

        elapsed = time.time() - start_time
        logger.info(
            "[图片分析] 调用完成: status_code=%s, 耗时=%.1fs",
            getattr(rsp, "status_code", None), elapsed,
        )
        logger.debug("[图片分析] 原始响应: %s", self._safe_to_dict(rsp))

        if rsp.status_code != HTTPStatus.OK:
            raise AIServiceException(
                f"图片分析失败: code={getattr(rsp, 'code', None)} "
                f"message={getattr(rsp, 'message', None)}"
            )

        # 提取模型输出文本
        text = self._extract_text(rsp)
        logger.info("[图片分析] 模型输出文本: %s", text[:300])
        if not text:
            raise AIServiceException("图片分析返回为空")

        # 解析 JSON（兼容模型偶尔输出多余说明文字）
        data = self._parse_json(text)
        if data is None:
            logger.warning("图片分析结果非 JSON，原文: %s", text)
            return ImageAnalysis(subject=text[:200], raw={"raw_text": text})

        # 颜色与关键物件统一为列表
        colors = data.get("colors") or []
        if isinstance(colors, str):
            colors = [c.strip() for c in colors.split(",") if c.strip()]
        key_objects = data.get("key_objects") or []
        if isinstance(key_objects, str):
            key_objects = [o.strip() for o in key_objects.split(",") if o.strip()]

        result = ImageAnalysis(
            subject=data.get("subject"),
            scene=data.get("scene"),
            mood=data.get("mood"),
            composition=data.get("composition"),
            colors=list(colors),
            key_objects=list(key_objects),
            raw=data,
        )
        logger.info(
            "[图片分析] 解析完成: subject=%s, scene=%s, mood=%s, colors=%s, objects=%s",
            result.subject, result.scene, result.mood,
            result.colors[:3], result.key_objects[:3],
        )
        return result

    async def analyze_for_revival(self, image_url: str) -> dict[str, Any]:
        """
        Photo Revival 专用深度分析。

        使用 REVIVAL_ANALYSIS_SYSTEM_PROMPT 调用 VL 模型，
        返回包含主体识别、核心元素、插画规则、英文提示词、诗意小字的完整结构。

        Args:
            image_url: 待分析的图片地址

        Returns:
            解析后的 dict，包含 subject_analysis / core_elements / rules /
            final_prompt / poetic_options / suggestions 等字段
        """
        return await asyncio.to_thread(self._analyze_revival_sync, image_url)

    def _analyze_revival_sync(self, image_url: str) -> dict[str, Any]:
        """同步执行 Photo Revival 深度分析"""
        from dashscope import MultiModalConversation
        from http import HTTPStatus

        api_key = settings.dashscope.api_key.get_secret_value()
        if not api_key:
            raise AIServiceException("DashScope API Key 未配置")

        messages = [
            {
                "role": "system",
                "content": [{"text": REVIVAL_ANALYSIS_SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [
                    {"image": image_url},
                    {"text": "请分析这张照片并按要求输出 JSON。"},
                ],
            },
        ]

        logger.info("[照片复兴分析] 调用 VL 模型: image_url=%s", image_url)
        logger.debug("[照片复兴分析] 完整 messages: %s", json.dumps(messages, ensure_ascii=False, default=str))

        start_time = time.time()

        try:
            rsp = MultiModalConversation.call(
                model=self.model,
                messages=messages,
                api_key=api_key,
            )
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("[照片复兴分析] 调用异常 (耗时 %.1fs): %s", elapsed, exc)
            raise AIServiceException(f"照片复兴分析调用失败: {exc}") from exc

        elapsed = time.time() - start_time
        logger.info(
            "[照片复兴分析] 调用完成: status_code=%s, 耗时=%.1fs",
            getattr(rsp, "status_code", None), elapsed,
        )

        if rsp.status_code != HTTPStatus.OK:
            raise AIServiceException(
                f"照片复兴分析失败: code={getattr(rsp, 'code', None)} "
                f"message={getattr(rsp, 'message', None)}"
            )

        text = self._extract_text(rsp)
        logger.info("[照片复兴分析] 模型输出文本(前300字): %s", text[:300])
        if not text:
            raise AIServiceException("照片复兴分析返回为空")

        data = self._parse_json(text)
        if data is None:
            logger.warning("[照片复兴分析] 结果非 JSON，原文: %s", text[:500])
            raise AIServiceException("照片复兴分析结果解析失败")

        logger.info(
            "[照片复兴分析] 解析完成: subject=%s, elements=%d, poetic=%d",
            str(data.get("subject_analysis", ""))[:50],
            len(data.get("core_elements", [])),
            len(data.get("poetic_options", [])),
        )
        return data

    async def analyze_for_editorial(self, image_url: str) -> dict[str, Any]:
        """
        City Editorial Poster 专用深度分析（城市/风景海报）。

        使用 EDITORIAL_ANALYSIS_SYSTEM_PROMPT 调用 VL 模型，
        返回面向上下分区编辑海报的结构化结果（主体分析、核心元素、插画提炼规则、
        英文提示词、诗意短句、使用建议）。

        Args:
            image_url: 待分析的图片地址

        Returns:
            解析后的 dict，包含 subject_analysis / core_elements / rules /
            final_prompt / poetic_options / suggestions 等字段
        """
        return await asyncio.to_thread(self._analyze_editorial_sync, image_url)

    def _analyze_editorial_sync(self, image_url: str) -> dict[str, Any]:
        """同步执行 City Editorial 深度分析"""
        from dashscope import MultiModalConversation
        from http import HTTPStatus

        api_key = settings.dashscope.api_key.get_secret_value()
        if not api_key:
            raise AIServiceException("DashScope API Key 未配置")

        messages = [
            {
                "role": "system",
                "content": [{"text": EDITORIAL_ANALYSIS_SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [
                    {"image": image_url},
                    {"text": "请分析这张城市或风景照片并按要求输出 JSON。"},
                ],
            },
        ]

        logger.info("[风景海报分析] 调用 VL 模型: image_url=%s", image_url)
        logger.debug("[风景海报分析] 完整 messages: %s", json.dumps(messages, ensure_ascii=False, default=str))

        start_time = time.time()

        try:
            rsp = MultiModalConversation.call(
                model=self.model,
                messages=messages,
                api_key=api_key,
            )
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("[风景海报分析] 调用异常 (耗时 %.1fs): %s", elapsed, exc)
            raise AIServiceException(f"风景海报分析调用失败: {exc}") from exc

        elapsed = time.time() - start_time
        logger.info(
            "[风景海报分析] 调用完成: status_code=%s, 耗时=%.1fs",
            getattr(rsp, "status_code", None), elapsed,
        )

        if rsp.status_code != HTTPStatus.OK:
            raise AIServiceException(
                f"风景海报分析失败: code={getattr(rsp, 'code', None)} "
                f"message={getattr(rsp, 'message', None)}"
            )

        text = self._extract_text(rsp)
        logger.info("[风景海报分析] 模型输出文本(前300字): %s", text[:300])
        if not text:
            raise AIServiceException("风景海报分析返回为空")

        data = self._parse_json(text)
        if data is None:
            logger.warning("[风景海报分析] 结果非 JSON，原文: %s", text[:500])
            raise AIServiceException("风景海报分析结果解析失败")

        logger.info(
            "[风景海报分析] 解析完成: subject=%s, elements=%d, poetic=%d",
            str(data.get("subject_analysis", ""))[:50],
            len(data.get("core_elements", [])),
            len(data.get("poetic_options", [])),
        )
        return data

    @staticmethod
    def _safe_to_dict(obj: Any) -> Any:
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

    @staticmethod
    def _extract_text(rsp: Any) -> str:
        """从 MultiModalConversation 响应中提取文本内容"""
        output = getattr(rsp, "output", None)
        if output is None:
            return ""
        choices = getattr(output, "choices", None) or (
            output.get("choices") if isinstance(output, dict) else None
        )
        if not choices:
            return ""
        first = choices[0]
        message = getattr(first, "message", None) or (
            first.get("message") if isinstance(first, dict) else None
        )
        if message is None:
            return ""
        content = getattr(message, "content", None) or (
            message.get("content") if isinstance(message, dict) else None
        )
        if not content:
            return ""
        # content 为列表，拼接 text 字段
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
                elif isinstance(item, str):
                    texts.append(item)
            return "".join(texts).strip()
        if isinstance(content, str):
            return content.strip()
        return ""

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any] | None:
        """尝试从模型输出中解析 JSON，兼容代码块包裹"""
        candidate = text.strip()
        # 去除可能的 ```json ... ``` 包裹
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if len(lines) >= 2:
                candidate = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # 尝试提取首个 {...} 片段
            start = candidate.find("{")
            end = candidate.rfind("}")
            if 0 <= start < end:
                try:
                    return json.loads(candidate[start : end + 1])
                except json.JSONDecodeError:
                    return None
            return None
