"""
3D 翻页画册 AI 分析服务

使用视觉模型分析照片，生成：
- 每张照片的 caption（标题）和描述
- 整体色彩主题（颜色方案）
- 情绪氛围（mood）
"""

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.flipbook import FlipbookPage, FlipbookProject

logger = logging.getLogger(__name__)


class FlipbookAIService:
    """画册 AI 分析服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def analyze_and_enhance(self, project_id: str) -> None:
        """
        分析画册中的所有照片，生成主题和 caption。

        流程：
        1. 获取画册和页面
        2. AI 智能排序照片（按游玩时间线 / 故事叙事逻辑，更新 page_order）
        3. 分析代表性照片 → 生成主题色和情绪
        4. 为每张照片生成 caption
        5. 更新数据库状态为 ready
        """
        # 获取画册
        from sqlalchemy import select
        result = await self.db.execute(
            select(FlipbookProject).where(FlipbookProject.project_id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            logger.error(f"[FlipbookAI] 画册不存在: {project_id}")
            return

        # 更新状态为 analyzing
        project.status = "analyzing"
        await self.db.flush()

        # 获取所有页面
        result = await self.db.execute(
            select(FlipbookPage)
            .where(FlipbookPage.project_id == project_id)
            .order_by(FlipbookPage.page_order)
        )
        pages = list(result.scalars().all())

        if not pages:
            logger.warning(f"[FlipbookAI] 画册没有页面: {project_id}")
            project.status = "ready"
            await self.db.commit()
            return

        try:
            # 1. AI 智能排序照片（失败时保持原顺序，不影响后续分析）
            photo_urls = [p.image_url for p in pages if p.image_url]
            if len(photo_urls) > 1:
                indices = await self.order_photos(photo_urls)
                # indices[i] = 原位置；将原位置的照片移动到新位置 i
                for new_order, old_idx in enumerate(indices):
                    pages[old_idx].page_order = new_order
                await self.db.flush()
                logger.info(f"[FlipbookAI] 页面顺序已按 AI 排序更新: {indices}")
                # 重新按新顺序读取页面
                result = await self.db.execute(
                    select(FlipbookPage)
                    .where(FlipbookPage.project_id == project_id)
                    .order_by(FlipbookPage.page_order)
                )
                pages = list(result.scalars().all())

            # 2. 分析代表性照片（第一张）生成主题
            first_page = pages[0]
            if first_page.image_url:
                theme = await self._analyze_theme(first_page.image_url, project.title)
                project.theme_json = json.dumps(theme, ensure_ascii=False)
                logger.info(f"[FlipbookAI] 生成主题: {theme}")

            # 3. 为每张照片生成 caption
            for page in pages:
                if page.image_url:
                    caption = await self._generate_caption(page.image_url)
                    page.caption = caption
                    logger.info(f"[FlipbookAI] 页面 {page.page_id} caption: {caption}")

            # 4. 更新状态为 ready
            project.status = "ready"
            await self.db.commit()
            logger.info(f"[FlipbookAI] 画册分析完成: {project_id}")

        except Exception as e:
            logger.error(f"[FlipbookAI] 分析失败: {e}", exc_info=True)
            project.status = "error"
            project.error_message = str(e)
            await self.db.commit()

    async def _analyze_theme(self, image_url: str, title: str) -> dict[str, Any]:
        """
        分析照片生成主题配置。

        返回：
        {
            "mood": "温暖/冷静/活力...",
            "pageColor": "#f5f1e6",
            "coverColor": "#d8d0bc",
            "backCoverColor": "#cbc1a9",
            "pageTexture": "纸质/纤维/平滑...",
        }
        """
        prompt = f"""Analyze this photo for a photo book theme. Respond in JSON format:

{{
  "mood": "one word describing the mood (warm/cool/vibrant/calm/elegant/playful)",
  "pageColor": "hex color for inner pages (light cream/beige/white based on photo tones)",
  "coverColor": "hex color for cover (darker, complementary to photo)",
  "backCoverColor": "hex color for back cover (solid, neutral)",
  "pageTexture": "texture style (paper/fiber/smooth/grainy)"
}}

Book title: {title}

Photo:
"""
        response = await self._call_vision_model(prompt=prompt, image_url=image_url)

        # 解析 JSON 响应
        try:
            # 尝试从响应中提取 JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            theme = json.loads(response.strip())

            # 提供默认值
            return {
                "mood": theme.get("mood", "elegant"),
                "pageColor": theme.get("pageColor", "#f5f1e6"),
                "coverColor": theme.get("coverColor", "#d8d0bc"),
                "backCoverColor": theme.get("backCoverColor", "#cbc1a9"),
                "pageTexture": theme.get("pageTexture", "paper"),
            }
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"[FlipbookAI] 主题解析失败，使用默认值: {e}")
            return {
                "mood": "elegant",
                "pageColor": "#f5f1e6",
                "coverColor": "#d8d0bc",
                "backCoverColor": "#cbc1a9",
                "pageTexture": "paper",
            }

    async def _generate_caption(self, image_url: str) -> str:
        """为照片生成简短标题（caption）"""
        prompt = """Generate a short, elegant caption for this photo (max 10 words). 
The caption should capture the essence or mood of the image.
Respond with ONLY the caption text, no quotes or extra punctuation.

Example captions:
- Sunset over the mountains
- Morning coffee ritual
- City lights at dusk
- A moment of peace
"""
        response = await self._call_vision_model(prompt=prompt, image_url=image_url)

        # 清理响应
        caption = response.strip().strip('"').strip("'").strip(".")

        # 限制长度
        if len(caption) > 100:
            caption = caption[:97] + "..."

        return caption or "Untitled"

    async def order_photos(self, photo_urls: list[str]) -> list[int]:
        """
        AI 智能排序照片。

        分析全部照片的内容，按照「游玩时间线 / 故事叙事逻辑」编排阅读顺序，
        让画册讲述一段完整的旅行故事。不限制图片数量。

        流程：
        1. 一次性将所有照片发给视觉模型排序；
        2. 若一次调用失败，降级为「逐张生成描述 → 文本排序」；
        3. 全部失败时返回原始顺序。

        Args:
            photo_urls: 照片 URL 列表（当前顺序）

        Returns:
            排序后的索引列表（如 [2, 0, 1]），失败时返回原始顺序 [0, 1, 2, ...]
        """
        count = len(photo_urls)
        if count <= 1:
            return list(range(count))

        logger.info(f"[FlipbookAI] 开始 AI 排序: 共 {count} 张，不限制数量")

        # 方案一：一次把所有照片发给视觉模型
        indices = await self._order_all_at_once(photo_urls)
        if indices is not None:
            logger.info(f"[FlipbookAI] AI 排序完成(整批): {indices}")
            return indices

        # 方案二：降级为「逐张生成描述 → 文本排序」（不受图片数量限制）
        logger.warning("[FlipbookAI] 整批排序失败，降级为描述排序")
        indices = await self._order_by_descriptions(photo_urls)
        if indices is not None:
            logger.info(f"[FlipbookAI] AI 排序完成(描述): {indices}")
            return indices

        logger.warning("[FlipbookAI] 排序全部失败，使用原始顺序")
        return list(range(count))

    async def _order_all_at_once(self, photo_urls: list[str]) -> list[int] | None:
        """一次把所有照片发给视觉模型，按游玩时间线 / 故事叙事排序"""
        count = len(photo_urls)

        prompt = f"""You are a photo book editor curating {count} travel photos into a photo book.

Work through these steps IN ORDER:

STEP 1 - VISUAL UNDERSTANDING: Analyze EVERY photo's content carefully, noting for each one: scene, objects, people, color tone, lighting, time of day, location and activity.

STEP 2 - SEMANTIC GROUPING: Group photos by semantic similarity of their content (e.g. all beach scenes together, all sunset shots together, all group portraits together, all food moments together).

STEP 3 - ORDER DECISION: Decide the final reading order following, in priority: natural TIMELINE of the trip, then THEMATIC/STORY logic, then visual aesthetics. Within each semantic group keep the chronological flow; between groups choose the order that tells the most coherent story (departure → journey → highlights → farewell) with smooth mood flow and visual variety.

Return ONLY a JSON array of 0-based indices covering ALL {count} photos exactly once, in the final reading order.
Example: [3, 0, 2, 1, 4]
Do NOT include any other text, explanation, or markdown."""

        response = await self._call_vision_model(prompt=prompt, photo_urls=photo_urls)
        return self._parse_index_array(response, count)

    async def _order_by_descriptions(self, photo_urls: list[str]) -> list[int] | None:
        """
        降级方案：逐张调用视觉模型生成一句话描述，
        再一次性把全部描述交给模型做文本排序（不受图片数量限制）。
        """
        count = len(photo_urls)

        # 1. 逐张生成描述
        descriptions: list[str] = []
        for i, url in enumerate(photo_urls):
            desc = await self._describe_photo(url)
            descriptions.append(desc or f"Photo {i + 1} (unrecognized)")
            logger.info(f"[FlipbookAI] 描述[{i}] {descriptions[-1][:80]}")

        # 2. 文本排序
        items = [
            {"index": i, "description": d} for i, d in enumerate(descriptions)
        ]
        prompt = f"""You are a photo book editor. Below are one-line descriptions of {count} travel photos (each "description" was generated by a vision model looking at the photo).

{json.dumps(items, ensure_ascii=False, indent=2)}

Work through these steps IN ORDER:

STEP 1 - UNDERSTANDING: For each photo, infer from its description the scene, objects, people, color tone and mood.

STEP 2 - SEMANTIC GROUPING: Group photos by semantic similarity (e.g. all beach scenes together, all sunset shots together, all group portraits together, all food moments together).

STEP 3 - ORDER DECISION: Decide the final reading order following, in priority: natural TIMELINE of the trip, then THEMATIC/STORY logic, then visual aesthetics. Within each semantic group keep the chronological flow; between groups choose the order that tells the most coherent story (departure → journey → highlights → farewell) with smooth mood flow and visual variety.

Return ONLY a JSON array of the "index" values, covering ALL {count} photos exactly once, in the final reading order.
Example: [3, 0, 2, 1, 4]
Do NOT include any other text, explanation, or markdown."""

        response = await self._call_vision_model(prompt=prompt)
        return self._parse_index_array(response, count)

    async def _describe_photo(self, image_url: str) -> str:
        """为单张照片生成一句话描述（场景 / 时间 / 活动）"""
        prompt = (
            "Describe this photo in ONE short sentence (max 15 words), "
            "focusing on the scene, time of day (morning/noon/evening/night), "
            "location and activity. Respond with ONLY the sentence."
        )
        response = await self._call_vision_model(prompt=prompt, image_url=image_url)
        desc = response.strip().strip('"').strip("'")
        return desc[:120] if desc else ""

    @staticmethod
    def _parse_index_array(response: str, total: int) -> list[int] | None:
        """
        从模型响应中解析 JSON 索引数组。

        兼容 markdown 围栏与前后多余文字；索引去重、补全缺失项。
        解析失败返回 None。
        """
        import re

        try:
            match = re.search(r"\[\s*\d[\d,\s]*\]", response or "")
            raw = match.group(0) if match else (response or "").strip()
            indices = json.loads(raw)
            if not isinstance(indices, list):
                raise ValueError("响应不是数组")

            seen: set[int] = set()
            ordered: list[int] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < total and idx not in seen:
                    seen.add(idx)
                    ordered.append(idx)
            # 补全缺失的索引（保持原相对顺序）
            for i in range(total):
                if i not in seen:
                    seen.add(i)
                    ordered.append(i)
            return ordered
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                f"[FlipbookAI] 排序响应解析失败: {e} | raw={response[:200]}"
            )
            return None

    async def _call_vision_model(
        self,
        prompt: str,
        image_url: str | None = None,
        photo_urls: list[str] | None = None,
    ) -> str:
        """
        调用千问视觉模型（qwen3-vl-plus）。

        支持单图（image_url）或多图（photo_urls）输入。

        使用 DashScope MultiModalConversation API。
        """
        import dashscope
        from dashscope import MultiModalConversation

        # 从内存缓存读取配置（管理后台可热更新；DB 为空时回退 .env）
        from app.services.model_config_store import model_config_store

        cfg = model_config_store.get_config("qianwen") or {}
        api_key = cfg.get("api_key") or settings.dashscope.api_key.get_secret_value()
        if not api_key:
            logger.error("[FlipbookAI] DashScope API Key 未配置")
            return ""

        model = cfg.get("model_vision") or settings.dashscope.model_vision
        workspace_id = cfg.get("workspace_id") or settings.dashscope.workspace_id
        region = cfg.get("region") or settings.dashscope.region

        # 设置 base URL（优先级：配置的 base_url > Workspace 专属端点 > 共享端点）
        from app.ai.dashscope_utils import normalize_dashscope_base_url

        cfg_base_url = (cfg.get("base_url") or "").strip()
        if cfg_base_url:
            dashscope.base_http_api_url = normalize_dashscope_base_url(cfg_base_url)
        elif workspace_id:
            dashscope.base_http_api_url = (
                f"https://{workspace_id}.{region}.maas.aliyuncs.com/api/v1"
            )
        else:
            dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

        logger.info(f"[FlipbookAI] 视觉模型: model={model}, base_url={dashscope.base_http_api_url}")

        # 构建消息内容：图片在前，文字在后
        content: list[dict] = []
        if photo_urls:
            for url in photo_urls:
                content.append({"image": url})
        elif image_url:
            content.append({"image": image_url})
        content.append({"text": prompt})

        messages = [{"role": "user", "content": content}]

        logger.info(f"[FlipbookAI] 调用视觉模型: model={model}, images={len(content) - 1}")

        try:
            # 在线程池中执行同步调用
            import asyncio
            response = await asyncio.to_thread(
                lambda: MultiModalConversation.call(
                    api_key=api_key,
                    model=model,
                    messages=messages,
                )
            )

            # 解析响应
            status_code = getattr(response, "status_code", 0)
            if status_code != 200:
                logger.error(f"[FlipbookAI] 视觉模型调用失败: {response}")
                return ""

            output = getattr(response, "output", None)
            if not output:
                return ""

            choices = getattr(output, "choices", [])
            if not choices:
                return ""

            message = choices[0].get("message", {}) if isinstance(choices[0], dict) else getattr(choices[0], "message", {})
            content = message.get("content", []) if isinstance(message, dict) else getattr(message, "content", [])

            # 提取文本内容
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        return item["text"]
                    elif hasattr(item, "text"):
                        return item.text

            return ""

        except Exception as e:
            logger.error(f"[FlipbookAI] 视觉模型调用异常: {e}", exc_info=True)
            return ""
