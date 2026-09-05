"""
IP 角色特征提取器

使用 DashScope qwen-vl-plus 分析用户照片中的人物，
提取角色特征用于 Q 版 IP 贴纸设计。

输出包含：
- character_prompt: 详细英文角色描述（用于后续生成保持一致性）
- character_description: 中文角色描述（展示给用户确认）
- key_features: 最具辨识度的特征列表
- suggested_stickers: 20 个建议的表情/姿态
"""

import json
import logging
import time
from typing import Any

from app.ai.dashscope_utils import run_blocking_with_timeout
from app.config import settings
from app.core.exceptions import AIServiceException

logger = logging.getLogger(__name__)


# 角色特征提取系统提示词
CHARACTER_EXTRACT_SYSTEM_PROMPT = """你是一个 IP 角色设计师。分析给定照片中的人物，提取以下角色特征用于 Q 版 IP 贴纸设计：

请输出 JSON 格式：
{
  "character_prompt": "详细的英文角色描述（100-200词），包括：发型（长度/分缝/刘海/发尾）、发色、脸型、眼睛特征（大小/形状）、眉毛形态、鼻子、嘴巴、体型、穿着（上衣款式颜色/下装款式颜色/鞋子）、标志性配饰（眼镜款式/帽子/耳环等）、肤色。描述要足够详细，使不同画师能画出一致的角色。",
  "character_description": "中文角色描述（50-100字），给用户确认用，如：Q版角色，短黑发波波头、圆脸、大眼睛、戴黑框圆眼镜、穿白色卫衣",
  "key_features": ["3-5个最具辨识度的视觉特征"],
  "suggested_stickers": [
    {"label": "开心大笑", "prompt_suffix": "laughing happily with eyes closed, mouth wide open"},
    {"label": "比心", "prompt_suffix": "making a heart shape with both hands, sweet smile"},
    {"label": "收到", "prompt_suffix": "saluting with one hand, determined expression"},
    {"label": "好耶", "prompt_suffix": "jumping with both arms raised high, excited face"},
    {"label": "冲冲冲", "prompt_suffix": "running forward with hair blowing back, determined look"},
    {"label": "疑惑", "prompt_suffix": "tilting head with question mark floating above, confused face"},
    {"label": "累趴了", "prompt_suffix": "lying face down on desk, exhausted, ZZZ symbols above"},
    {"label": "拿捏", "prompt_suffix": "confident smirk, adjusting glasses with one finger"},
    {"label": "谢谢你", "prompt_suffix": "hands together bowing slightly, grateful expression"},
    {"label": "对不起", "prompt_suffix": "hands together with apologetic pout, small tear drop"},
    {"label": "在吗", "prompt_suffix": "peeking from the side, waving one hand, curious look"},
    {"label": "我可以", "prompt_suffix": "giving thumbs up with confident wink"},
    {"label": "爱了爱了", "prompt_suffix": "hands on cheeks with heart eyes, blushing"},
    {"label": "太难了", "prompt_suffix": "holding head in despair, sweat drops falling"},
    {"label": "人间蒸发", "prompt_suffix": "body dissolving into dotted lines, fading away"},
    {"label": "等一下", "prompt_suffix": "one palm forward in stop gesture, serious expression"},
    {"label": "早上好", "prompt_suffix": "waving cheerfully, small sun icon beside head"},
    {"label": "晚安", "prompt_suffix": "sleeping on pillow, peaceful face, moon and stars above"},
    {"label": "辛苦了", "prompt_suffix": "offering a hot drink with both hands, warm smile"},
    {"label": "没问题", "prompt_suffix": "arms crossed confidently, big grin, OK gesture"}
  ]
}

注意：
1. 只描述可见的视觉特征，不猜测性格
2. character_prompt 必须英文，足够详细确保角色一致性
3. suggested_stickers 固定输出 20 个，label 用中文，prompt_suffix 用英文描述动作和表情
4. 请仅输出 JSON，不要其他内容"""


class IPCharacterAnalyzer:
    """IP 角色特征提取器"""

    DEFAULT_MODEL = settings.dashscope.model_vision

    def __init__(self, model: str | None = None) -> None:
        self.model = model or self.DEFAULT_MODEL

    async def extract_character(self, image_url: str) -> dict[str, Any]:
        """
        提取角色特征。

        Args:
            image_url: 用户照片 URL

        Returns:
            dict 包含 character_prompt, character_description, key_features, suggested_stickers
        """
        return await run_blocking_with_timeout(
            self._extract_sync, image_url,
            timeout=60.0, retries=2, label="IP角色特征提取",
        )

    def _extract_sync(self, image_url: str) -> dict[str, Any]:
        """同步调用 DashScope VL 模型（在线程池中运行）"""
        from dashscope import MultiModalConversation
        from http import HTTPStatus

        # 从独立视觉理解配置读取（后台可热更新；未单独配置时回退千问/.env）
        import dashscope
        from app.ai.dashscope_utils import normalize_dashscope_base_url
        from app.services.model_config_store import model_config_store

        cfg = model_config_store.get_vision_config()
        if not cfg.get("enabled", True):
            raise AIServiceException("视觉理解模型已停用，请先在后台配置中开启")
        api_key = cfg.get("api_key") or settings.dashscope.api_key.get_secret_value()
        if not api_key:
            raise AIServiceException("DashScope API Key 未配置")

        base_url = (cfg.get("base_url") or "").strip()
        dashscope.base_http_api_url = (
            normalize_dashscope_base_url(base_url)
            if base_url
            else "https://dashscope.aliyuncs.com/api/v1"
        )
        self.model = (cfg.get("model_vision") or "").strip() or self.model

        messages = [
            {
                "role": "system",
                "content": [{"text": CHARACTER_EXTRACT_SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [
                    {"image": image_url},
                    {"text": "请分析这张照片中的人物，提取角色特征用于 IP 贴纸设计。"},
                ],
            },
        ]

        logger.info("[IP角色分析] 调用 VL 模型: image_url=%s", image_url)
        start_time = time.time()

        try:
            rsp = MultiModalConversation.call(
                model=self.model,
                messages=messages,
                api_key=api_key,
            )
        except Exception as exc:
            elapsed = time.time() - start_time
            logger.error("[IP角色分析] 调用异常 (%.1fs): %s", elapsed, exc)
            raise AIServiceException(f"IP角色分析调用失败: {exc}") from exc

        elapsed = time.time() - start_time
        logger.info(
            "[IP角色分析] 调用完成: status_code=%s, 耗时=%.1fs",
            getattr(rsp, "status_code", None), elapsed,
        )

        if rsp.status_code != HTTPStatus.OK:
            raise AIServiceException(
                f"IP角色分析失败: code={getattr(rsp, 'code', None)} "
                f"message={getattr(rsp, 'message', None)}"
            )

        text = self._extract_text(rsp)
        logger.info("[IP角色分析] 模型输出(前300字): %s", text[:300])
        if not text:
            raise AIServiceException("IP角色分析返回为空")

        data = self._parse_json(text)
        if data is None:
            raise AIServiceException("IP角色分析结果解析失败")

        # 验证必要字段
        if "character_prompt" not in data:
            raise AIServiceException("IP角色分析缺少 character_prompt")
        if "suggested_stickers" not in data:
            # 补充默认 20 个表情
            data["suggested_stickers"] = self._default_stickers()

        logger.info(
            "[IP角色分析] 解析完成: prompt_len=%d, stickers=%d",
            len(data.get("character_prompt", "")),
            len(data.get("suggested_stickers", [])),
        )
        return data

    @staticmethod
    def _extract_text(rsp: Any) -> str:
        """从 MultiModalConversation 响应中提取文本"""
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
        """尝试从模型输出中解析 JSON"""
        candidate = text.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if len(lines) >= 2:
                candidate = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if 0 <= start < end:
                try:
                    return json.loads(candidate[start:end + 1])
                except json.JSONDecodeError:
                    return None
            return None

    @staticmethod
    def _default_stickers() -> list[dict]:
        """默认 20 个表情配置"""
        return [
            {"label": "开心大笑", "prompt_suffix": "laughing happily with eyes closed, mouth wide open"},
            {"label": "比心", "prompt_suffix": "making a heart shape with both hands, sweet smile"},
            {"label": "收到", "prompt_suffix": "saluting with one hand, determined expression"},
            {"label": "好耶", "prompt_suffix": "jumping with both arms raised high, excited face"},
            {"label": "冲冲冲", "prompt_suffix": "running forward with hair blowing back, determined look"},
            {"label": "疑惑", "prompt_suffix": "tilting head with question mark floating above, confused face"},
            {"label": "累趴了", "prompt_suffix": "lying face down on desk, exhausted, ZZZ symbols above"},
            {"label": "拿捏", "prompt_suffix": "confident smirk, adjusting glasses with one finger"},
            {"label": "谢谢你", "prompt_suffix": "hands together bowing slightly, grateful expression"},
            {"label": "对不起", "prompt_suffix": "hands together with apologetic pout, small tear drop"},
            {"label": "在吗", "prompt_suffix": "peeking from the side, waving one hand, curious look"},
            {"label": "我可以", "prompt_suffix": "giving thumbs up with confident wink"},
            {"label": "爱了爱了", "prompt_suffix": "hands on cheeks with heart eyes, blushing"},
            {"label": "太难了", "prompt_suffix": "holding head in despair, sweat drops falling"},
            {"label": "人间蒸发", "prompt_suffix": "body dissolving into dotted lines, fading away"},
            {"label": "等一下", "prompt_suffix": "one palm forward in stop gesture, serious expression"},
            {"label": "早上好", "prompt_suffix": "waving cheerfully, small sun icon beside head"},
            {"label": "晚安", "prompt_suffix": "sleeping on pillow, peaceful face, moon and stars above"},
            {"label": "辛苦了", "prompt_suffix": "offering a hot drink with both hands, warm smile"},
            {"label": "没问题", "prompt_suffix": "arms crossed confidently, big grin, OK gesture"},
        ]
