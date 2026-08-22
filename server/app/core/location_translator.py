"""
地址翻译器

将用户填写的地名（可能为中文，如「昆明/中国」）交由文本大模型
翻译为英文的「City, Country」格式（如「Kunming, China」），
供冰箱贴等需要英文城市名排版的技能使用。

使用 DashScope 文本生成模型（qwen-turbo）完成翻译。
"""

import asyncio
import functools
import logging
from typing import Any

from app.config import settings
from app.config.dashscope import MODEL_TEXT
from app.core.exceptions import AIServiceException

logger = logging.getLogger(__name__)

# 翻译系统提示词：约束输出为「City, Country」英文格式，不加解释
TRANSLATE_SYSTEM_PROMPT = (
    "你是一个地名翻译专家。用户会给出城市和国家（可能为中文，以斜杠或逗号分隔），"
    "请将其翻译为英文的『City, Country』格式。"
    "只输出英文结果本身，不要任何解释、引号或额外符号。"
    "示例："
    "昆明/中国 -> Kunming, China；"
    "巴黎/法国 -> Paris, France；"
    "东京/日本 -> Tokyo, Japan。"
    "如果用户已经提供英文，则原样返回。"
)


async def translate_location(raw: str) -> str:
    """
    异步翻译地名为英文「City, Country」。

    Args:
        raw: 用户填写的原始地点，如「昆明/中国」

    Returns:
        英文地点字符串，如「Kunming, China」；输入为空时返回空字符串。
    """
    text = (raw or "").strip()
    if not text:
        return ""
    # 同一地点多次转换不重复调大模型（进程内 LRU 缓存，线程安全：纯 dict 读）
    return await asyncio.to_thread(_translate_cached, text)


def _translate_sync(text: str) -> str:
    """同步翻译（在线程池中执行）"""
    from http import HTTPStatus

    from dashscope import Generation

    api_key = settings.dashscope.api_key.get_secret_value()
    if not api_key:
        raise AIServiceException("DashScope API Key 未配置")

    messages = [
        {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
        {"role": "user", "content": f"请翻译：{text}"},
    ]

    logger.info("[地址翻译] 调用 %s: %s", MODEL_TEXT, text)
    try:
        rsp = Generation.call(model=MODEL_TEXT, messages=messages, api_key=api_key)
    except Exception as exc:
        raise AIServiceException(f"地址翻译调用失败: {exc}") from exc

    if rsp.status_code != HTTPStatus.OK:
        raise AIServiceException(
            f"地址翻译失败: code={getattr(rsp, 'code', None)} "
            f"message={getattr(rsp, 'message', None)}"
        )

    content = _extract_content(rsp)
    result = (content or "").strip()
    if not result:
        logger.warning("[地址翻译] 返回为空，回退原文: %s", text)
        return text

    # 容错：若模型附带了多余解释文字，仅截取首个 "X, Y" 形态片段
    comma_idx = result.find(",")
    if comma_idx != -1:
        tail = result[comma_idx + 1:].strip()
        if tail and "," not in tail:
            result = f"{result[:comma_idx].strip()}, {tail}"
    logger.info("[地址翻译] 结果: %s -> %s", text, result)
    return result


@functools.lru_cache(maxsize=512)
def _translate_cached(text: str) -> str:
    """同步翻译带 LRU 缓存（同地点不重复调大模型）"""
    return _translate_sync(text)


def _extract_content(rsp: Any) -> str:
    """从 Generation 响应中提取文本内容（兼容对象与字典两种形态）"""
    output = getattr(rsp, "output", None)
    if output is None:
        return ""
    choices = getattr(output, "choices", None)
    if choices is None and isinstance(output, dict):
        choices = output.get("choices")
    if not choices:
        return ""

    first = choices[0]
    message = getattr(first, "message", None)
    if message is None and isinstance(first, dict):
        message = first.get("message")
    if message is None:
        return ""

    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    if isinstance(content, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return content or ""
