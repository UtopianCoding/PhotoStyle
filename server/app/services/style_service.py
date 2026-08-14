"""
风格转换服务

编排完整的风格转换流程：
1. 创建任务（pending）
2. 后台处理：分析图片 -> 生成提示词 -> 调用 AI Provider -> 下载结果 -> MinIO 上传 -> 落库 -> 标记成功
3. 查询任务状态
4. 取消任务

convert 接口立即返回 pending 任务，真正的处理在 BackgroundTasks 中执行；
process_style_task 作为模块级异步函数，自建数据库会话，避免复用已关闭的请求会话。
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.image_analyzer import ImageAnalyzer
from app.ai.provider_manager import ProviderManager
from app.ai.schemas import ImageOptions, ImageProviderRequest
from app.core.exceptions import (
    AIServiceException,
    ForbiddenException,
    ImageNotFoundException,
    RateLimitExceededException,
    SkillNotFoundException,
    TaskNotFoundException,
)
from app.core.image_processor import ImageProcessor
from app.core.skill_engine import SkillEngine
from app.core.task_manager import TaskManager
from app.database import async_session_maker
from app.models.style_task import StyleTask
from app.repositories.image_repo import ImageRepository
from app.repositories.style_repo import StyleRepository
from app.schemas.style import (
    AnalyzeRequest,
    AnalyzeResponse,
    ConvertRequest,
    ConvertResponse,
    TaskResult,
    TaskStatusResponse,
)

logger = logging.getLogger(__name__)

# -------------------- 内容类别判定辅助 --------------------

# 城市/风景/自然风光 的中英文关键词命中列表（任意命中即可推荐 city-editorial）
LANDSCAPE_HINT_KEYWORDS = [
    # 中文
    "城市", "建筑", "天际线", "街道", "夜景", "大厦", "摩天", "桥梁", "河流",
    "山川", "山脉", "湖泊", "海洋", "大海", "海岸", "海滩", "草原", "森林",
    "日落", "日出", "夕阳", "朝霞", "晚霞", "云海", "雪山", "冰川", "瀑布",
    "田野", "乡村", "田园", "梯田", "沙漠", "星空", "月亮", "圆月", "新月",
    "塔", "古建", "城墙", "寺庙", "宫殿", "古镇",
    # 英文
    "city", "building", "skyscraper", "street", "skyline", "night view",
    "bridge", "river", "mountain", "lake", "sea", "ocean", "beach", "coast",
    "forest", "snow", "sunset", "sunrise", "moon", "cloud", "landscape",
    "skyline", "tower", "temple", "cathedral", "desert", "waterfall",
]


def _classify_image_category(analysis_text: str) -> str:
    """
    根据轻量分析拼接文本，判断内容属于 "landscape"（城市/风景）还是 "portrait"（人物/其他）。

    命中 LANDSCAPE_HINT_KEYWORDS 中任意关键词即视为 landscape；
    若关键词都没命中，再通过"明确提到人物类关键词"判为 portrait，否则默认 portrait。
    """
    if not analysis_text:
        return "portrait"
    text_lower = analysis_text.lower()
    if any(kw.lower() in text_lower for kw in LANDSCAPE_HINT_KEYWORDS):
        return "landscape"
    # 兜底：如果明确提到 person / girl / boy / man / woman / portrait / 人物 / 女孩 / 男孩 等
    portrait_kw = (
        "person", "people", "girl", "boy", "man", "woman", "lady",
        "portrait", "face", "character",
        "人物", "人像", "女孩", "男孩", "女人", "男人", "女士", "男士", "肖像", "脸部",
    )
    if any(kw in analysis_text for kw in portrait_kw):
        return "portrait"
    return "portrait"


def _pick_skill_id_by_category(category: str) -> str:
    """根据内容类别选择技能 ID"""
    if category == "landscape":
        return "city-editorial"
    return "photo-revival"


class StyleService:
    """风格转换服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = StyleRepository(db)
        self.image_repo = ImageRepository(db)
        self.task_manager = TaskManager(db)
        self.skill_engine = SkillEngine()
        self.analyzer = ImageAnalyzer()
        self.provider_manager = ProviderManager()
        self.processor = ImageProcessor()

    # -------------------- 分析入口 --------------------

    async def analyze(self, user_id: str, payload: AnalyzeRequest) -> AnalyzeResponse:
        """
        分析图片，生成结构化提示词 + 诗意小字选项，并推荐最佳匹配技能。

        流程：
        1. 校验图片归属
        2. 轻量调用 VL 模型分析图片（subject / scene / mood / colors / key_objects）
        3. 基于关键词命中判断内容类别：landscape（城市/风景） vs portrait（人物/其他）
        4. 选择推荐技能：landscape → city-editorial；portrait → photo-revival
        5. 根据推荐技能调用对应深度分析 prompt，输出完整结构化提示词
        6. 返回主体分析、核心元素、插画规则、英文提示词、诗意小字 + recommended_skill_id

        Args:
            user_id: 用户ID
            payload: 分析请求

        Returns:
            AnalyzeResponse 含完整分析结果 + 推荐技能 ID
        """
        # 1. 校验图片存在且属于当前用户
        image = await self.image_repo.get_by_image_id(payload.image_id)
        if image is None:
            raise ImageNotFoundException(f"图片 [{payload.image_id}] 不存在")
        if image.user_id != user_id:
            raise ForbiddenException("无权操作该图片")

        # 2. 先轻量分析，得到 subject / scene / mood / colors / key_objects，用于内容分类
        logger.info("[分析] 开始轻量分类分析: image_id=%s, image_url=%s", payload.image_id, image.original_url)
        try:
            quick = await self.analyzer.analyze(image.original_url)
            quick_bundle = " ".join(
                str(x) for x in [
                    quick.subject, quick.scene, quick.mood, quick.composition,
                    " ".join(quick.colors or []),
                    " ".join(quick.key_objects or []),
                ] if x
            )
        except Exception as exc:
            # 轻量分析失败也不阻塞，按 portrait 默认走 photo-revival
            logger.warning("[分析] 轻量分类失败，回退默认技能: %s", exc)
            quick_bundle = ""

        # 3. 分类并选择技能：用户指定了有效技能则优先使用，否则按内容自动推荐
        category = _classify_image_category(quick_bundle)
        auto_skill_id = _pick_skill_id_by_category(category)

        # 所有可用技能 ID（与 skills 目录一致）
        available_skills = {"photo-revival", "city-editorial", "photo-abstract-editorial"}
        requested_skill = (payload.skill_id or "").strip()
        if requested_skill in available_skills:
            skill_id = requested_skill
            logger.info("[分析] 使用用户指定技能: %s", skill_id)
        else:
            skill_id = auto_skill_id
        logger.info("[分析] 内容类别判定: category=%s, auto_skill=%s, 实际使用 skill=%s",
                    category, auto_skill_id, skill_id)

        # 4. 调用对应深度分析 prompt
        if skill_id == "city-editorial":
            analysis_data = await self.analyzer.analyze_for_editorial(image.original_url)
        elif skill_id == "photo-abstract-editorial":
            analysis_data = await self.analyzer.analyze_for_abstract(image.original_url)
        else:
            analysis_data = await self.analyzer.analyze_for_revival(image.original_url)

        # 5. 如果有额外提示词，追加到 final_prompt
        final_prompt = analysis_data.get("final_prompt", "")
        if payload.extra_prompt and payload.extra_prompt.strip():
            final_prompt = final_prompt.rstrip(".") + f". Additional requirement: {payload.extra_prompt.strip()}."
            analysis_data["final_prompt"] = final_prompt

        logger.info("[分析] 完成: skill=%s, final_prompt 长度=%d, poetic_options=%d",
                     skill_id, len(final_prompt), len(analysis_data.get("poetic_options", [])))

        return AnalyzeResponse(
            recommended_skill_id=skill_id,
            subject_analysis=analysis_data.get("subject_analysis", ""),
            core_elements=analysis_data.get("core_elements", []),
            rules=analysis_data.get("rules", {}),
            special_notes=analysis_data.get("special_notes", ""),
            final_prompt=final_prompt,
            poetic_options=analysis_data.get("poetic_options", []),
            suggestions=analysis_data.get("suggestions", []),
        )

    # -------------------- 转换入口 --------------------

    async def convert(
        self, user_id: str, payload: ConvertRequest
    ) -> ConvertResponse:
        """
        创建风格转换任务。

        校验图片归属与每日额度后创建 pending 任务，立即返回 task_id；
        真正的生成流程由调用方通过 process_style_task 后台触发。

        Args:
            user_id: 用户ID
            payload: 转换请求

        Returns:
            ConvertResponse（含 task_id，状态为 pending）
        """
        # 1. 校验图片存在且属于当前用户
        image = await self.image_repo.get_by_image_id(payload.image_id)
        if image is None:
            raise ImageNotFoundException(f"图片 [{payload.image_id}] 不存在")
        if image.user_id != user_id:
            raise ForbiddenException("无权操作该图片")

        # 2. 校验技能存在
        try:
            self.skill_engine.load_skill(payload.skill_id)
        except SkillNotFoundException:
            raise
        except Exception as exc:
            raise SkillNotFoundException(f"技能 [{payload.skill_id}] 加载失败: {exc}") from exc

        # 3. 校验每日额度（通过图片所属用户）
        # 注：每日用量统计由调用方在成功时累加，此处仅做上限校验
        # 留作扩展：可在此查询用户当日用量

        # 4. 序列化选项
        options_dict = payload.options.model_dump()

        # 4.1 如果有预分析结果，存入 options_json 中传递给后台任务
        if payload.final_prompt:
            options_dict["_final_prompt"] = payload.final_prompt
        if payload.poetic_text:
            options_dict["_poetic_text"] = payload.poetic_text

        # 5. 创建任务
        task = await self.task_manager.create_task(
            user_id=user_id,
            image_id=payload.image_id,
            skill_id=payload.skill_id,
            provider=payload.provider,
            extra_prompt=payload.extra_prompt,
            options_json=json.dumps(options_dict, ensure_ascii=False),
        )
        await self.db.commit()

        return ConvertResponse(
            task_id=task.task_id,
            status=task.status,
            skill_id=task.skill_id,
            provider=task.provider,
            estimated_time=30,
        )

    # -------------------- 后台处理 --------------------

    async def run_pipeline(self, task_id: str) -> None:
        """
        执行完整生成流程。

        步骤：
        1. 标记任务 running / analyzing
        2. 视觉分析原图
        3. 生成提示词
        4. 调用 Provider 生成图像
        5. 下载结果并上传 MinIO
        6. 创建 StyleResult 记录
        7. 标记任务 success

        任意步骤失败均标记任务 failed 并写入错误信息。
        """
        task = await self.repo.get_task(task_id)
        if task is None:
            logger.error("任务不存在: %s", task_id)
            return

        try:
            await self._execute(task)
        except Exception as exc:
            logger.exception("任务处理失败: %s", task_id)
            await self.repo.update_task_status(
                task_id,
                status="failed",
                stage="failed",
                error_code="PIPELINE_ERROR",
                error_message=str(exc),
            )
            await self.db.commit()

    async def _execute(self, task: StyleTask) -> None:
        """执行各阶段"""
        # 获取原图地址
        image = await self.image_repo.get_by_image_id(task.image_id)
        if image is None:
            raise ImageNotFoundException(f"图片 [{task.image_id}] 不存在")
        image_url = image.original_url

        # 选项
        options = json.loads(task.options_json) if task.options_json else {}

        # 判断是否有预分析结果（从 task 字段中获取）
        # final_prompt 和 poetic_text 存储在 task 的 extra 字段中
        # 通过 options_json 中的 _final_prompt 和 _poetic_text 传递
        final_prompt = options.pop("_final_prompt", None)
        poetic_text = options.pop("_poetic_text", None)

        if final_prompt:
            # 有预分析结果，跳过分析阶段，直接使用提供的提示词
            logger.info("[风格转换] 使用预分析提示词, task_id=%s, prompt=%s", task.task_id, final_prompt[:200])

            await self.repo.update_task_status(
                task.task_id, status="running", stage="generating", progress=30
            )
            await self.db.commit()

            # 如果有诗意小字，追加到提示词
            prompt = final_prompt
            if poetic_text:
                prompt = prompt.rstrip(".") + f". A tiny handwritten poetic note in faint gray ink at the bottom edge reads: '{poetic_text}'."
                logger.info("[风格转换] 追加诗意小字: %s", poetic_text)

            analysis: dict[str, Any] = {}
        else:
            # 无预分析结果，走原有流程：分析 → 生成提示词
            # 阶段1：分析
            await self.repo.update_task_status(
                task.task_id, status="running", stage="analyzing", progress=10
            )
            await self.db.commit()

            analysis: dict[str, Any] = {}
            try:
                logger.info("[风格转换] 阶段1: 开始图片分析, task_id=%s, image_url=%s", task.task_id, image_url)
                analysis_result = await self.analyzer.analyze(image_url)
                analysis = analysis_result.model_dump(exclude_none=True)
                logger.info("[风格转换] 阶段1: 图片分析完成, task_id=%s, subject=%s", task.task_id, analysis.get("subject"))
            except Exception as exc:
                logger.warning("[风格转换] 阶段1: 图片分析失败，降级为空分析: %s", exc)
                analysis = {}

            # 阶段2：生成提示词
            await self.repo.update_task_status(
                task.task_id, stage="generating", progress=30
            )
            await self.db.commit()

            prompt = self.skill_engine.generate_prompt(
                image_url=image_url,
                skill_id=task.skill_id,
                extra_prompt=task.extra_prompt,
                options=options,
                image_analysis=analysis,
            )
            logger.info("[风格转换] 阶段2: 提示词生成完成, task_id=%s, prompt=%s", task.task_id, prompt[:300])

        # 阶段3：调用 Provider 生成
        logger.info("[风格转换] 阶段3: 开始调用 Provider, task_id=%s, provider=%s", task.task_id, task.provider)
        provider_request = ImageProviderRequest(
            prompt=prompt,
            image_url=image_url,
            options=ImageOptions(
                ratio=options.get("ratio", "3:4"),
                num_results=options.get("num_results", 1),
            ),
        )
        response = await self.provider_manager.generate(
            provider_request, preferred=task.provider
        )
        logger.info("[风格转换] 阶段3: Provider 返回, task_id=%s, status=%s, results=%d", task.task_id, response.status, len(response.results or []))

        if response.status != "success" or not response.results:
            raise AIServiceException(
                response.error or "AI 生成未返回结果"
            )

        # 阶段4：下载并上传结果
        await self.repo.update_task_status(
            task.task_id, stage="uploading", progress=70
        )
        await self.db.commit()

        for idx, result in enumerate(response.results):
            result_bytes, content_type = await self._download(result.url)
            ext = self._content_type_to_ext(content_type)
            result_url = await self._upload_result(
                task.user_id, result_bytes, ext, content_type
            )

            # 生成缩略图
            thumbnail_url = None
            try:
                thumb_bytes = await asyncio.to_thread(
                    self.processor.generate_thumbnail, result_bytes
                )
                thumbnail_url = await self._upload_result(
                    task.user_id, thumb_bytes, "jpg", "image/jpeg", prefix="results/thumbnails"
                )
            except Exception as exc:
                logger.warning("结果缩略图生成失败: %s", exc)

            await self.repo.create_result(
                result_id=uuid.uuid4().hex,
                task_id=task.task_id,
                user_id=task.user_id,
                image_id=task.image_id,
                skill_id=task.skill_id,
                provider=task.provider,
                result_url=result_url,
                thumbnail_url=thumbnail_url,
                prompt_used=prompt,
                analysis_json=json.dumps(analysis, ensure_ascii=False) if analysis else None,
                provider_response=json.dumps(
                    response.raw_response or {}, ensure_ascii=False, default=str
                ),
                favorite=False,
                credits_used=1,
            )

        # 阶段5：完成
        await self.repo.update_task_status(
            task.task_id, status="success", stage="done", progress=100
        )
        await self.db.commit()

    # -------------------- 任务状态 --------------------

    async def get_task_status(
        self, user_id: str, task_id: str
    ) -> TaskStatusResponse:
        """查询任务状态与结果"""
        task = await self.repo.get_task(task_id)
        if task is None:
            raise TaskNotFoundException(f"任务 [{task_id}] 不存在")
        if task.user_id != user_id:
            raise ForbiddenException("无权访问该任务")

        results = await self.repo.get_results_by_task(task_id)
        result_models = [
            TaskResult(
                result_id=r.result_id,
                result_url=r.result_url,
                thumbnail_url=r.thumbnail_url,
                favorite=r.favorite,
                created_at=r.created_at,
            )
            for r in results
        ]

        image = await self.repo.get_image(task.image_id)

        return TaskStatusResponse(
            task_id=task.task_id,
            image_id=task.image_id,
            original_url=image.original_url if image else "",
            status=task.status,
            stage=task.stage,
            progress=task.progress,
            message=task.error_message,
            results=result_models,
            error=task.error_message if task.status == "failed" else None,
        )

    async def cancel_task(self, user_id: str, task_id: str) -> TaskStatusResponse:
        """取消任务"""
        task = await self.repo.get_task(task_id)
        if task is None:
            raise TaskNotFoundException(f"任务 [{task_id}] 不存在")
        if task.user_id != user_id:
            raise ForbiddenException("无权取消该任务")

        if task.status not in ("pending", "running"):
            # 已终态，直接返回当前状态
            return await self.get_task_status(user_id, task_id)

        await self.repo.update_task_status(
            task_id, status="canceled", stage="canceled", completed_at=None
        )
        await self.db.commit()
        return await self.get_task_status(user_id, task_id)

    # -------------------- 工具方法 --------------------

    @staticmethod
    async def _download(url: str) -> tuple[bytes, str]:
        """异步下载图片字节，返回 (字节流, content_type)"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg")
            return resp.content, content_type

    def _upload_result(
        self,
        user_id: str,
        data: bytes,
        ext: str,
        content_type: str,
        prefix: str = "results",
    ) -> Any:
        """异步上传结果到对象存储，返回 awaitable"""
        return asyncio.to_thread(self._do_upload, user_id, data, ext, content_type, prefix)

    def _do_upload(
        self, user_id: str, data: bytes, ext: str, content_type: str, prefix: str
    ) -> str:
        """实际上传，返回公开访问 URL"""
        from app.core.storage import get_storage_provider

        storage = get_storage_provider()

        date = datetime.utcnow().strftime("%Y%m%d")
        key = f"{prefix}/{user_id}/{date}/{uuid.uuid4().hex}.{ext}"
        return storage.upload(key, data, content_type)

    @staticmethod
    def _content_type_to_ext(content_type: str) -> str:
        """content-type 转扩展名"""
        mapping = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
            "image/bmp": "bmp",
        }
        # 兼容带 charset 的情形
        ct = content_type.split(";")[0].strip().lower()
        return mapping.get(ct, "jpg")


# ============================================================
# 后台任务入口：自建会话，供 BackgroundTasks 调用
# ============================================================

async def process_style_task(task_id: str) -> None:
    """
    后台执行风格转换任务。

    独立创建数据库会话，避免复用请求会话（请求结束后会话已关闭）。
    用法：
        background_tasks.add_task(process_style_task, task_id)
    """
    async with async_session_maker() as db:
        service = StyleService(db)
        await service.run_pipeline(task_id)
        await db.commit()
