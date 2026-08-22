"""
IP 贴纸图像生成服务

负责：
- 生成 IP 母版（照片 → VL 分析 → Q 版角色图）
- 批量生成贴纸（基于锁定的母版 character_prompt）
- 下载结果 + 上传 MinIO
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.ip_character_analyzer import IPCharacterAnalyzer
from app.ai.provider_manager import ProviderManager
from app.ai.schemas import ImageOptions, ImageProviderRequest
from app.core.exceptions import AIServiceException
from app.core.image_processor import ImageProcessor
from app.models.ip_master_template import IPMasterTemplate
from app.repositories.ip_chat_repo import IPChatRepository

logger = logging.getLogger(__name__)

# 共享 HTTP 客户端（复用 style_service 的模式）
_HTTP_CLIENT: "httpx.AsyncClient | None" = None


def _get_http_client() -> "httpx.AsyncClient":
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            follow_redirects=True,
        )
    return _HTTP_CLIENT


# IP 贴纸固定风格前缀
BASE_STYLE_PROMPT = (
    "Black and white hand-drawn chibi/Q-version character sticker, "
    "clean irregular pen line art, minimal light gray shading only, "
    "big head small body proportions, white background, "
    "simple cute manga style. No 3D, no complex coloring, no background scene. "
)

# 一致性锁定提示片段（每次生成必加）
CONSISTENCY_PROMPT = (
    "CRITICAL: The character MUST exactly match this description — "
    "same face shape, hairstyle, bangs, glasses, clothing, accessories, "
    "body proportions, and art style. Do NOT change any character features. "
    "Only modify the pose, expression, and emotion-related accessories. "
    "ANATOMY: The character MUST have exactly 2 hands, 2 arms, 2 legs, and 1 head. "
    "Do NOT generate extra hands, arms, legs, fingers, or any additional body parts. "
    "Each limb must be clearly visible and correctly attached to the body. "
    "Avoid floating limbs, disconnected hands, or extra appendages. "
)


class IPStickerGenService:
    """IP 贴纸图像生成服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = IPChatRepository(db)
        self.provider_manager = ProviderManager()
        self.character_analyzer = IPCharacterAnalyzer()
        self.processor = ImageProcessor()

    # -------------------- IP 母版生成 --------------------

    async def generate_base_image(
        self,
        user_id: str,
        session_id: str,
        image_url: str,
        modification_feedback: str | None = None,
        previous_template: IPMasterTemplate | None = None,
    ) -> dict[str, Any]:
        """
        生成 IP 母版。

        流程：
        1. VL 模型分析照片提取角色特征
        2. 构造 Q 版角色提示词
        3. 图像生成模型生成母版图
        4. 下载结果上传 MinIO
        5. 返回结果 dict

        Args:
            user_id: 用户ID
            session_id: 会话ID
            image_url: 用户照片 URL
            modification_feedback: 用户修改意见（修改场景）
            previous_template: 上一版母版（修改场景，用于继承 character_prompt）

        Returns:
            {"image_url", "thumbnail_url", "character_prompt",
             "character_description", "generation_prompt"}
        """
        # 1. 角色特征提取（修改场景继承上一版 prompt，仅叠加修改意见）
        if modification_feedback and previous_template:
            character_prompt = previous_template.character_prompt
            character_description = previous_template.character_description or ""
            logger.info("[IP母版] 修改场景，继承 character_prompt，叠加反馈: %s",
                        modification_feedback[:200])
        else:
            logger.info("[IP母版] 提取角色特征: image_url=%s", image_url)
            character_data = await self.character_analyzer.extract_character(image_url)
            character_prompt = character_data["character_prompt"]
            character_description = character_data.get("character_description", "")
            logger.info("[IP母版] 角色特征提取完成: prompt_len=%d", len(character_prompt))

        # 2. 构造生成提示词
        prompt = f"{BASE_STYLE_PROMPT}Character: {character_prompt}. {CONSISTENCY_PROMPT}"
        if modification_feedback:
            prompt += f" Revise based on feedback: {modification_feedback}."

        # 3. 调用图像生成（1:1 正方形，图生图参考原照片）
        logger.info("[IP母版] 开始图像生成: prompt=%s", prompt[:200])
        request = ImageProviderRequest(
            prompt=prompt,
            image_url=image_url,
            options=ImageOptions(ratio="1:1", num_results=1),
        )
        response = await self.provider_manager.generate(request, preferred="qianwen")

        if response.status != "success" or not response.results:
            raise AIServiceException(
                response.error or "IP 母版生成未返回结果"
            )

        # 4. 下载结果 + 上传 MinIO
        result_url = response.results[0].url
        result_bytes, content_type = await self._download(result_url)
        stored_url = await self._upload_to_storage(
            user_id, result_bytes, "png", content_type, prefix="ip-stickers/masters"
        )
        thumbnail_url = await self._generate_and_upload_thumbnail(user_id, result_bytes)

        logger.info("[IP母版] 生成完成: url=%s", stored_url)

        return {
            "image_url": stored_url,
            "thumbnail_url": thumbnail_url,
            "character_prompt": character_prompt,
            "character_description": character_description,
            "generation_prompt": prompt,
        }

    # -------------------- 贴纸批量生成 --------------------

    async def generate_sticker_batch(
        self,
        user_id: str,
        session_id: str,
        template: IPMasterTemplate,
        sticker_configs: list[dict[str, Any]],
        batch_type: str = "test_batch",
    ) -> list[dict[str, Any]]:
        """
        批量生成贴纸。

        Args:
            template: 已锁定的 IP 母版
            sticker_configs: [{"index": 1, "label": "开心大笑", "prompt_suffix": "..."}]
            batch_type: test_batch / full_batch / redraw

        Returns:
            [{"sticker_id", "url", "thumbnail_url", "index", "label", "status", "error"?}]
        """
        # 一致性保证：所有贴纸共享母版的 character_prompt + 风格前缀
        base_prompt = (
            f"{BASE_STYLE_PROMPT}"
            f"Character (MUST match exactly): {template.character_prompt}. "
            f"{CONSISTENCY_PROMPT}"
        )

        # 并发控制：最多同时 3 个图像生成请求（避免 DashScope 限频）
        semaphore = asyncio.Semaphore(3)

        async def gen_one(config: dict) -> dict[str, Any]:
            async with semaphore:
                try:
                    prompt = f"{base_prompt} Pose/Expression: {config['prompt_suffix']}."
                    request = ImageProviderRequest(
                        prompt=prompt,
                        image_url=template.master_image_url,
                        options=ImageOptions(ratio="1:1", num_results=1),
                    )
                    response = await self.provider_manager.generate(
                        request, preferred="qianwen"
                    )
                    if response.status != "success" or not response.results:
                        raise AIServiceException(
                            response.error or "贴纸生成未返回结果"
                        )

                    # 下载 + 上传
                    result_url = response.results[0].url
                    result_bytes, ct = await self._download(result_url)
                    stored_url = await self._upload_to_storage(
                        user_id, result_bytes, "png", ct,
                        prefix=f"ip-stickers/{session_id}"
                    )
                    thumb_url = await self._generate_and_upload_thumbnail(
                        user_id, result_bytes
                    )

                    # 写库
                    sticker = await self.repo.create_sticker(
                        session_id=session_id,
                        template_id=template.template_id,
                        user_id=user_id,
                        sticker_index=config["index"],
                        label=config["label"],
                        generation_prompt=prompt,
                        result_url=stored_url,
                        batch_type=batch_type,
                        thumbnail_url=thumb_url,
                        status="success",
                    )

                    return {
                        "sticker_id": sticker.sticker_id,
                        "url": stored_url,
                        "thumbnail_url": thumb_url,
                        "index": config["index"],
                        "label": config["label"],
                        "status": "success",
                    }

                except Exception as exc:
                    logger.error(
                        "[贴纸生成] 失败: index=%d, label=%s, error=%s",
                        config["index"], config["label"], exc,
                    )
                    # 记录失败到数据库
                    try:
                        sticker = await self.repo.create_sticker(
                            session_id=session_id,
                            template_id=template.template_id,
                            user_id=user_id,
                            sticker_index=config["index"],
                            label=config["label"],
                            generation_prompt="",
                            result_url="",
                            batch_type=batch_type,
                            status="failed",
                            error_message=str(exc),
                        )
                    except Exception:
                        pass

                    return {
                        "sticker_id": None,
                        "index": config["index"],
                        "label": config["label"],
                        "status": "failed",
                        "error": str(exc),
                    }

        results = await asyncio.gather(
            *(gen_one(c) for c in sticker_configs),
            return_exceptions=True,
        )

        final: list[dict[str, Any]] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final.append({
                    "sticker_id": None,
                    "index": sticker_configs[i]["index"],
                    "label": sticker_configs[i]["label"],
                    "status": "failed",
                    "error": str(r),
                })
            else:
                final.append(r)

        return final

    # -------------------- 工具方法 --------------------

    @staticmethod
    async def _download(url: str) -> tuple[bytes, str]:
        """下载图片"""
        client = _get_http_client()
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/png")
        return resp.content, content_type

    async def _upload_to_storage(
        self,
        user_id: str,
        data: bytes,
        ext: str,
        content_type: str,
        prefix: str = "ip-stickers",
    ) -> str:
        """上传到 MinIO/OSS"""
        from app.core.storage import get_storage_provider
        storage = get_storage_provider()

        date = datetime.utcnow().strftime("%Y%m%d")
        key = f"{prefix}/{user_id}/{date}/{uuid.uuid4().hex}.{ext}"

        def _do_upload():
            return storage.upload(key, data, content_type)

        return await asyncio.to_thread(_do_upload)

    async def _generate_and_upload_thumbnail(
        self, user_id: str, result_bytes: bytes
    ) -> str | None:
        """生成缩略图并上传"""
        try:
            thumb_bytes = await asyncio.to_thread(
                self.processor.generate_thumbnail, result_bytes
            )
            return await self._upload_to_storage(
                user_id, thumb_bytes, "jpg", "image/jpeg",
                prefix="ip-stickers/thumbnails"
            )
        except Exception as exc:
            logger.warning("IP 贴纸缩略图生成失败: %s", exc)
            return None
