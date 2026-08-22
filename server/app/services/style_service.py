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
import os
import time
import uuid
from datetime import datetime, date
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.image_analyzer import ImageAnalyzer
from app.ai.provider_manager import ProviderManager
from app.ai.schemas import ImageOptions, ImageProviderRequest
from app.config import settings
from app.core.exceptions import (
    AIServiceException,
    ForbiddenException,
    ImageNotFoundException,
    InsufficientCreditsException,
    RateLimitExceededException,
    SkillNotFoundException,
    TaskNotFoundException,
)
from app.core.image_processor import ImageProcessor
from app.core.location_translator import translate_location
from app.core.skill_engine import SkillEngine
from app.core.task_manager import TaskManager
from app.database import async_session_maker
from app.models.conversation import ModelInteraction
from app.models.style_task import StyleTask
from app.models.user import User
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

# -------------------- 共享 HTTP 客户端（连接池复用） --------------------

_HTTP_CLIENT: "httpx.AsyncClient | None" = None


def _get_http_client() -> "httpx.AsyncClient":
    """复用带连接池的 httpx 客户端，避免每次下载都新建 TCP/TLS 连接。"""
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            follow_redirects=True,
        )
    return _HTTP_CLIENT


async def close_http_client() -> None:
    """应用关闭时释放共享客户端。"""
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None and not _HTTP_CLIENT.is_closed:
        await _HTTP_CLIENT.aclose()
    _HTTP_CLIENT = None


logger = logging.getLogger(__name__)

# -------------------- 内容类别判定辅助 --------------------


def _pick_skill_id_by_category(category: str) -> str:
    """根据内容类别选择技能 ID"""
    if category == "landscape":
        return "city-editorial"
    return "photo-revival"


class StyleService:
    """风格转换服务"""

    # 参考图 URL 缓存（skill_id -> url），避免每次生成都重复上传
    _reference_image_cache: dict[str, str] = {}

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

        # 2. 选择技能：用户指定了有效技能则使用，否则走默认（photo-revival）
        # 优化：跳过独立的 classify_category VL 调用（3-8s），
        # 各深度分析 prompt 已在 JSON 输出中包含 category 字段，一次调用同时完成分类+分析。
        available_skills = {
            "photo-revival",
            "photo-relic-editorial",
            "city-editorial",
            "photo-abstract-editorial",
            "fridge-magnet",
            "ink-minimalist",
            "memory-postcard",
            "scenes-gathered-zine",
        }
        requested_skill = (payload.skill_id or "").strip()
        if requested_skill in available_skills:
            skill_id = requested_skill
            logger.info("[分析] 使用用户指定技能: %s", skill_id)
        else:
            skill_id = "photo-revival"
        logger.info("[分析] 使用技能: %s, image_id=%s", skill_id, payload.image_id)

        # 3. 调用对应深度分析 prompt
        if skill_id == "city-editorial":
            analysis_data = await self.analyzer.analyze_for_editorial(image.original_url)
        elif skill_id == "photo-abstract-editorial":
            analysis_data = await self.analyzer.analyze_for_abstract(image.original_url)
        elif skill_id == "fridge-magnet":
            # 冰箱贴：固定模板，无需 VL 深度分析；
            # 地址由文本模型翻译为英文后注入模板的 {{LOCATION}} 占位符。
            raw_location = (payload.location or "").strip()
            if not raw_location:
                raise AIServiceException("请填写冰箱贴拍摄地点，例如：昆明/中国")
            try:
                location_en = await translate_location(raw_location)
            except Exception as exc:
                logger.warning("[分析] 地址翻译失败，使用原文: %s", exc)
                location_en = raw_location

            final_prompt = await self.skill_engine.generate_prompt_async(
                image_url=image.original_url,
                skill_id=skill_id,
                extra_prompt=payload.extra_prompt,
                options={"location": location_en},
            )
            analysis_data = {
                "subject_analysis": (
                    f"旅行冰箱贴海报，地点：{location_en}。"
                    "下半部分严格保留您的原图（人物、景观、构图、色调不变）；"
                    "上半部分中等明度蓝紫/灰蓝哑光背景，居中一枚偏小的不规则珐琅质感冰箱贴，"
                    "提取当地代表性景观并适当融入原图人物；底部仅细衬线英文城市名排版。"
                ),
                "core_elements": [
                    "下半部分原图严格保留（不重绘、不调色）",
                    "上半哑光蓝紫/灰蓝背景",
                    "居中偏小不规则珐琅冰箱贴（轻微金属描边）",
                    "底部细衬线 City, Country 排版（细线+小菱形分隔）",
                ],
                "rules": {
                    "composition": "竖版 2:3，上下严格分区：上 45% 背景+冰箱贴，下 55% 原图",
                    "mainArea": "下半 55% 为原始照片，保持人物/景观/构图/色调不变",
                    "negativeSpace": "上半背景均匀哑光蓝紫/灰蓝，无渐变噪点",
                    "style": "珐琅质感冰箱贴，仅轻微金属描边，温润不刺眼",
                    "typography": "底部仅 City, Country，高级细衬线、宽字距，细线+小菱形分隔",
                    "avoid": "过度装饰、卡通/3D/矢量图标感、过金属/过暗/过亮",
                },
                "special_notes": "底部文字仅保留城市与国家英文名，不追加其他文字；冰箱贴大小与文字位置逐张统一。",
                "final_prompt": final_prompt,
                "poetic_options": [],
                "suggestions": [
                    "若冰箱贴偏弱，可在额外要求中追加：make the fridge magnet slightly larger and more vivid enamel",
                    "若底部文字位置偏移，可追加：bottom typography vertically centered and consistent",
                ],
            }
        elif skill_id == "ink-minimalist":
            # 水墨扁平重构插画：固定模板风格，无需 VL 深度分析；
            # 直接通过 SkillEngine 按模板 + 原图地址生成最终提示词。
            final_prompt = await self.skill_engine.generate_prompt_async(
                image_url=image.original_url,
                skill_id=skill_id,
                extra_prompt=payload.extra_prompt,
                options={},
            )
            analysis_data = {
                "subject_analysis": (
                    "水墨扁平重构插画。提取原图景物解构为极简几何形态，"
                    "运用分层平涂柔和色块与毛笔淡墨晕染笔触，"
                    "在米白哑光特种纸留白底色上呈现干净高级的学术感视觉效果。"
                ),
                "core_elements": [
                    "米白哑光特种纸质感底色，大面积纯留白",
                    "居中偏上的极简几何插画，严格复刻原图配色",
                    "无锐角硬边，全圆润流畅弧线组合",
                    "分层平涂色块 + 毛笔淡墨晕染笔触",
                    "底部居中排版：优雅衬线手写体英文标题 + 小号无衬线英文描述短句",
                ],
                "rules": {
                    "composition": "竖版 2:3，主体居中偏上，四周大量留白",
                    "mainArea": "几何形态解构原图上半景物，摒弃锐利硬边",
                    "negativeSpace": "米白色哑光特种纸底色，大面积纯留白",
                    "style": "分层平涂色块 + 毛笔淡墨晕染，色彩如水墨洇散自然过渡",
                    "typography": "画面最底端居中排版，首行衬线手写体英文标题，次行小号无衬线英文描述",
                    "avoid": "锐利硬边、细碎纹理、冗余杂物、复杂光影、多余装饰元素",
                },
                "special_notes": "彻底剔除所有细碎纹理、冗余杂物及复杂光影，仅保留纯粹的结构神韵与情感内核。",
                "final_prompt": final_prompt,
                "poetic_options": [],
                "suggestions": [
                    "若色块过渡不够自然，可在额外要求中追加：make the ink wash blending softer and more gradient-like",
                    "若留白比例不足，可追加：increase negative space around the illustration with wider margins",
                ],
            }
        elif skill_id == "memory-postcard":
            # 视觉记忆明信片：固定模板风格，无需 VL 深度分析；
            # 直接通过 SkillEngine 按模板 + 原图地址生成最终提示词。
            final_prompt = await self.skill_engine.generate_prompt_async(
                image_url=image.original_url,
                skill_id=skill_id,
                extra_prompt=payload.extra_prompt,
                options={},
            )
            analysis_data = {
                "subject_analysis": (
                    "编辑式视觉记忆明信片。忠实保留原图作为事实锚点，"
                    "搭配源自原图色彩与空间关系的水彩抽象记忆面板，"
                    "整体呈现安静、诗意、现代的编辑式档案作品质感。"
                ),
                "core_elements": [
                    "原图忠实保留（人物、建筑、光线、色彩关系不变）",
                    "抽象水彩记忆面板（神似而非形似，节奏/体量/氛围重新表达）",
                    "三枚手绘水彩色块（情感记忆色 + 深色结构色 + 浅色中性色）",
                    "英文衬线标题（2-5词，克制手写钢笔风格）",
                    "安静留白呼吸区（32%-40%，源自原图氛围温度）",
                ],
                "rules": {
                    "composition": "竖版 3:4，自适应双面板布局（横版左右分/竖版上下分）",
                    "photoRegion": "原图忠实保留，仅允许等比缩放和克制裁切",
                    "companionPanel": "抽象水彩记忆场域，母题占面板 35%-50%，源自原图视觉事实",
                    "colorSystem": "仅从原照片提取配色，降低饱和度，和谐排列",
                    "typography": "英文衬线标题 2-5 词，克制手写风格，位于面板内母题下方或侧边",
                    "ground": "源自原图氛围温度的淡色底面（冷雾白/暖阳象牙/灰绿薄雾/淡蓝水洗）",
                    "avoid": "重画原图/发明场景/渐变溶解/撕边投影/1:1水彩复制/密集装饰",
                },
                "special_notes": "整体如一件保存完好的视觉记忆器物，不是装饰过的照片。记忆面板通过缩减、半透明、断裂轮廓、位移、节奏、体量、色彩记忆重新表达原图精神。",
                "final_prompt": final_prompt,
                "poetic_options": [],
                "suggestions": [
                    "若记忆面板过于具象，可追加：increase abstraction level, use rhythm and mass rather than literal shapes",
                    "若色块与面板不够融合，可追加：embed swatches within the field's natural flow, not as isolated chips",
                ],
            }
        elif skill_id == "marker-child-doodle":
            # 马克笔童画：固定模板风格，无需 VL 深度分析；
            # 直接通过 SkillEngine 按模板 + 原图地址 + 签名生成最终提示词。
            raw_signature = (payload.signature or "").strip() or "Utopian"
            final_prompt = await self.skill_engine.generate_prompt_async(
                image_url=image.original_url,
                skill_id=skill_id,
                extra_prompt=payload.extra_prompt,
                options={"signature": raw_signature},
            )
            analysis_data = {
                "subject_analysis": (
                    "马克笔童画风格。把真实照片转换成粗轮廓、完整色块、手涂边缘的马克笔画，"
                    "像从儿童速写本上撕下来的马克笔页。"
                ),
                "core_elements": [
                    "石板灰蓝粗轮廓线（粗、钝、抖、粗细不匀，局部积墨）",
                    "马克笔平涂色块（填满为主，减少白点白洞白丝）",
                    "Q版夸张比例（头大身小脖子短，团块手，方块眼）",
                    "环境删除，仅保留互动道具和支撑面线",
                    "右下角潦草签名 wibi",
                ],
                "rules": {
                    "composition": "1:1 方形，白纸或黑底（根据原图明暗自动选择）",
                    "outline": "石板灰蓝粗轮廓，粗细不匀，整体连续只有少量自然断口",
                    "colorBlock": "马克笔平涂填满，手绘感集中在外围边缘错位和溢出",
                    "palette": "石板灰蓝线 + 人物肤色 + 一个服装主色 + 黑色",
                    "signature": "右下角潦草 wibi，歪斜带拖尾手势",
                    "avoid": "渐变/精致数码线稿/均匀虚线/色块大面积留白/半身补腿/删除宠物",
                },
                "special_notes": "原图决定内容（画谁画什么），参考图只决定画法（怎样画）。半身照片不补出腿脚，宠物同框时人和动物都要画。",
                "final_prompt": final_prompt,
                "poetic_options": [],
                "suggestions": [
                    "若轮廓太细太均匀，可追加：make outlines thicker, rougher, and more uneven with ink pooling",
                    "若色块不够饱满，可追加：fill color blocks more completely, reduce white spots and gaps",
                ],
            }
        elif skill_id == "scenes-gathered-zine":
            # 实景拼贴：固定模板风格，无需 VL 深度分析；
            # 直接通过 SkillEngine 按模板 + 原图地址生成最终提示词。
            final_prompt = await self.skill_engine.generate_prompt_async(
                image_url=image.original_url,
                skill_id=skill_id,
                extra_prompt=payload.extra_prompt,
                options={},
            )
            analysis_data = {
                "subject_analysis": (
                    "实景拼贴海报。忠实保留原图照片作为视觉锚点，"
                    "搭配大面积抽象插画场域重新诠释场景元素，"
                    "以一个高饱和色作为构图结构，可见手撕纤维边缘，"
                    "奶油色纸面大面积留白，整体安静、触感、沉思。"
                ),
                "core_elements": [
                    "照片忠实保留（主体、空间关系、地平线、视线方向不变）",
                    "大面积抽象插画场域（45-70%，中等抽象度，去除60-80%细节）",
                    "一个高饱和色作为构图结构（与原图色彩关联）",
                    "可见手撕纤维边缘（照片与纸面过渡）",
                    "克制的微文字系统（2-5词，衬线/打字机字体）",
                ],
                "rules": {
                    "composition": "竖版 3:5，照片约占 30-50%，插画场域约占 45-70%",
                    "photoRegion": "照片忠实保留，不重绘不滤镜化，保留原始场景辨识度",
                    "illustrationField": "一种主要插画语法（剪影/轮廓/色域/节奏/剪纸），活跃墨水占15-35%",
                    "chromaticStructure": "仅一个额外高饱和色，必须与插画共享源形状，不可漂浮装饰",
                    "tornEdge": "可见手撕轮廓，不规则缺口+纤维羽化边，占照片周长35-70%",
                    "avoid": "数码拼贴效果/投影/装饰边框/渐变背景/矢量风格/超过一个额外色",
                },
                "special_notes": "复杂场景（密集树木/人群）需进一步简化：保留一个主体树冠+1-3个方向性枝条姿态，省略85-95%的单独叶片。",
                "final_prompt": final_prompt,
                "poetic_options": [],
                "suggestions": [
                    "若撕纸边缘不够明显，可追加：make the torn paper edge more prominent and fibrous along the photo boundary",
                    "若插画过于写实，可追加：increase abstraction level, merge details into larger masses, use flat ink or cut-paper grammar",
                ],
            }
        else:
            analysis_data = await self.analyzer.analyze_for_revival(image.original_url)

        # 4. 如果有额外提示词，追加到 final_prompt
        final_prompt = analysis_data.get("final_prompt", "")
        if payload.extra_prompt and payload.extra_prompt.strip():
            final_prompt = final_prompt.rstrip(".") + f". Additional requirement: {payload.extra_prompt.strip()}."
            analysis_data["final_prompt"] = final_prompt

        # 5. 从深度分析结果中提取类别，用于推荐技能（仅当用户未指定技能时）
        # 各深度分析 prompt 已在 JSON 中输出 category 字段
        if not requested_skill:
            detected_category = analysis_data.get("category", "portrait")
            skill_id = _pick_skill_id_by_category(detected_category)
            logger.info("[分析] 深度分析检测到类别: %s, 推荐技能: %s", detected_category, skill_id)

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
            skill_config = await self.skill_engine.load_skill_async(payload.skill_id)
        except SkillNotFoundException:
            raise
        except Exception as exc:
            raise SkillNotFoundException(f"技能 [{payload.skill_id}] 加载失败: {exc}") from exc

        # 3. 校验每日额度（仅非管理员用户）
        stmt = select(User).where(User.user_id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise ForbiddenException("用户不存在")
        
        if not user.is_admin:
            # 检查是否需要重置每日使用次数（如果 updated_at 不是今天）
            today = date.today()
            last_usage_date = user.updated_at.date() if user.updated_at else None
            
            if last_usage_date != today:
                # 重置为 0
                user.usage_today = 0
            
            # 检查是否超过每日限制
            daily_limit = settings.rate_limit.free_user_daily_limit
            if user.usage_today >= daily_limit:
                raise RateLimitExceededException(
                    f"今日转换次数已达上限（{daily_limit} 次），请明天再试"
                )
            
            # 检查积分余额（每次转换消耗 2 积分）
            credit_cost = 2
            if user.credits < credit_cost:
                raise InsufficientCreditsException(
                    f"积分不足，当前余额 {user.credits}，需要 {credit_cost} 积分。请先充值"
                )

        # 4. 序列化选项
        options_dict = payload.options.model_dump()

        # 4.0 冰箱贴等需要地点的技能：把拍摄地点透传到后台任务，
        # 供 _execute 阶段权威重生成提示词（即便前端传入了旧风格的 finalPrompt 也不会用错）。
        if payload.location:
            options_dict["location"] = payload.location
        
        # 马克笔童画需要签名：透传到后台任务
        if payload.signature:
            options_dict["signature"] = payload.signature

        # 4.1 以技能声明的输出比例为准（前端通常不单独设置比例）。
        # 例如冰箱贴/城市海报声明 2:3，必须确保实际生成尺寸为 2:3 而非默认 3:4。
        if skill_config and skill_config.ratio:
            options_dict["ratio"] = skill_config.ratio

        # 4.1 如果有预分析结果，存入 options_json 中传递给后台任务
        if payload.final_prompt:
            options_dict["_final_prompt"] = payload.final_prompt
        if payload.poetic_text:
            options_dict["_poetic_text"] = payload.poetic_text
        # 重新生成的修改意见：透传到后台任务，_execute 阶段会叠加到原提示词后交给模型
        if payload.feedback:
            options_dict["_feedback"] = payload.feedback

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

        # 从 options_json 中取出前端透传的预分析提示词 / 诗意小字 / 重新生成意见
        final_prompt = options.pop("_final_prompt", None)
        poetic_text = options.pop("_poetic_text", None)
        feedback = options.pop("_feedback", None)

        # 加载技能配置，判断是否需要分析图片
        need_analysis = True
        try:
            skill_config = await self.skill_engine.load_skill_async(task.skill_id)
            need_analysis = skill_config.need_analysis
            logger.info("[风格转换] 技能配置: skill_id=%s, need_analysis=%s", task.skill_id, need_analysis)
        except Exception as exc:
            logger.warning("[风格转换] 加载技能配置失败，默认需要分析: %s", exc)

        # 基础提示词构建
        if final_prompt:
            # 预分析 / 重新生成：直接使用传入的完整提示词，跳过 VL 深度分析。
            # 重新生成时 final_prompt 即上一次生成的完整提示词，叠加用户意见后整体交给模型。
            logger.info("[风格转换] 使用预分析/重生成提示词, task_id=%s, prompt=%s", task.task_id, final_prompt[:200])
            await self.repo.update_task_status(
                task.task_id, status="running", stage="generating", progress=30
            )
            await self.db.commit()
            prompt = final_prompt
            analysis: dict[str, Any] = {}
        elif not need_analysis:
            # 技能配置标记为不需要分析：跳过 VL 分析，直接使用模板生成提示词
            logger.info("[风格转换] 技能无需分析，跳过 VL 分析, skill_id=%s", task.skill_id)
            await self.repo.update_task_status(
                task.task_id, status="running", stage="generating", progress=30
            )
            await self.db.commit()
            # 从数据库读取的提示词模板生成最终提示词（而非空字符串）
            prompt = await self.skill_engine.generate_prompt_async(
                image_url=image_url,
                skill_id=task.skill_id,
                extra_prompt=task.extra_prompt,
                options=options,
                image_analysis={},
            )
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

            # 阶段2：生成提示词（仅更新 progress，无需额外 commit，最终统一提交）
            await self.repo.update_task_status(
                task.task_id, stage="generating", progress=30
            )
            await self.db.flush()

            prompt = await self.skill_engine.generate_prompt_async(
                image_url=image_url,
                skill_id=task.skill_id,
                extra_prompt=task.extra_prompt,
                options=options,
                image_analysis=analysis,
            )
            logger.info("[风格转换] 阶段2: 提示词生成完成, task_id=%s, prompt=%s", task.task_id, prompt[:300])

        # 阶段2.5：冰箱贴首次生成的模板重生成（仅当未传入 final_prompt 时，即首次生成）
        # 传入 final_prompt 的重新生成场景会直接走上面的 final_prompt 分支，不再重跑模板。
        if task.skill_id == "fridge-magnet" and not final_prompt:
            raw_loc = options.get("location") or ""
            if raw_loc:
                try:
                    loc_en = await translate_location(raw_loc)
                except Exception as exc:
                    logger.warning("[风格转换] 冰箱贴地点翻译失败，使用原文: %s", exc)
                    loc_en = raw_loc
                prompt = await self.skill_engine.generate_prompt_async(
                    image_url=image_url,
                    skill_id=task.skill_id,
                    extra_prompt=task.extra_prompt,
                    options={"location": loc_en},
                )
                logger.info("[风格转换] 冰箱贴权威重生成提示词, task_id=%s, location=%s", task.task_id, loc_en)
            elif not prompt:
                # 既无地点也无预分析提示词：退回模板默认（City, Country）
                prompt = await self.skill_engine.generate_prompt_async(
                    image_url=image_url,
                    skill_id=task.skill_id,
                    extra_prompt=task.extra_prompt,
                    options={},
                )

        # 水墨扁平重构插画首次生成：固定模板，跳过 VL 分析后直接按模板生成提示词
        if task.skill_id == "ink-minimalist" and not final_prompt and not prompt:
            prompt = await self.skill_engine.generate_prompt_async(
                image_url=image_url,
                skill_id=task.skill_id,
                extra_prompt=task.extra_prompt,
                options={},
            )
            logger.info("[风格转换] 水墨扁平重构插画权威重生成提示词, task_id=%s", task.task_id)

        # 视觉记忆明信片首次生成：固定模板，跳过 VL 分析后直接按模板生成提示词
        if task.skill_id == "memory-postcard" and not final_prompt and not prompt:
            prompt = await self.skill_engine.generate_prompt_async(
                image_url=image_url,
                skill_id=task.skill_id,
                extra_prompt=task.extra_prompt,
                options={},
            )
            logger.info("[风格转换] 视觉记忆明信片权威重生成提示词, task_id=%s", task.task_id)

        # 马克笔童画首次生成：固定模板，跳过 VL 分析后直接按模板生成提示词
        if task.skill_id == "marker-child-doodle" and not final_prompt and not prompt:
            signature = options.get("signature", "Utopian")
            prompt = await self.skill_engine.generate_prompt_async(
                image_url=image_url,
                skill_id=task.skill_id,
                extra_prompt=task.extra_prompt,
                options={"signature": signature},
            )
            logger.info("[风格转换] 马克笔童画权威重生成提示词, task_id=%s, signature=%s", task.task_id, signature)

        # 实景拼贴首次生成：固定模板，跳过 VL 分析后直接按模板生成提示词
        if task.skill_id == "scenes-gathered-zine" and not final_prompt and not prompt:
            prompt = await self.skill_engine.generate_prompt_async(
                image_url=image_url,
                skill_id=task.skill_id,
                extra_prompt=task.extra_prompt,
                options={},
            )
            logger.info("[风格转换] 实景拼贴权威重生成提示词, task_id=%s", task.task_id)

        # 阶段2.6：统一追加诗意小字与重新生成意见（仅在尚未包含时追加，避免重复）
        if poetic_text and "handwritten poetic note" not in prompt:
            prompt = (
                prompt.rstrip(".")
                + f". A tiny handwritten poetic note in faint gray ink at the bottom edge reads: '{poetic_text}'."
            )
        if feedback and feedback.strip():
            prompt = (
                prompt.rstrip(".")
                + f". Revise the previous version based on these adjustments: {feedback.strip()}."
            )
            logger.info("[风格转换] 叠加重新生成意见, task_id=%s, feedback=%s", task.task_id, feedback[:200])

        # 阶段3：调用 Provider 生成
        started_at = time.monotonic()
        logger.info("[风格转换] 阶段3: 开始调用 Provider, task_id=%s, provider=%s", task.task_id, task.provider)

        # 加载风格参考图（仅对明确需要参考图的技能加载）
        # 注意：使用内存缓存，首次调用后会缓存 URL，修改 SKILL.md 后需重启服务
        _SKIP_REF_IMAGE_SKILLS = {"marker-child-doodle", "scenes-gathered-zine"}
        if task.skill_id not in _SKIP_REF_IMAGE_SKILLS:
            reference_images = await self._get_reference_images(task.skill_id)
        else:
            reference_images = []
        if reference_images:
            logger.info("[风格转换] 使用 %d 张参考图, skill_id=%s", len(reference_images), task.skill_id)

        provider_request = ImageProviderRequest(
            prompt=prompt,
            image_url=image_url,
            reference_images=reference_images,
            options=ImageOptions(
                ratio=options.get("ratio", "3:4"),
                num_results=options.get("num_results", 1),
            ),
        )
        try:
            response = await self.provider_manager.generate(
                provider_request, preferred=task.provider
            )
            logger.info("[风格转换] 阶段3: Provider 返回, task_id=%s, status=%s, results=%d", task.task_id, response.status, len(response.results or []))

            if response.status != "success" or not response.results:
                raise AIServiceException(
                    response.error or "AI 生成未返回结果"
                )
        except Exception as exc:
            # 阶段3 调用失败：记录一次「失败」的模型交互（输入已知，无输出）
            await self._record_interaction(
                task=task,
                image_url=image_url,
                prompt=prompt,
                extra_prompt=task.extra_prompt,
                feedback=feedback,
                options=options,
                status="failed",
                error_message=str(exc),
                duration_ms=int((time.monotonic() - started_at) * 1000),
            )
            raise

        # 阶段4：先用 Provider 临时 URL 立即写库，用户秒看结果；
        # 后台异步下载+上传到永久存储后替换 URL。
        await self.repo.update_task_status(
            task.task_id, stage="uploading", progress=70
        )
        await self.db.flush()

        # 快速路径：立即写入结果记录（使用 Provider 临时 URL，通常有效期 24h+）
        result_records: list[tuple[str, str]] = []  # (result_id, provider_url)
        analysis_json_str = json.dumps(analysis, ensure_ascii=False) if analysis else None
        provider_resp_str = json.dumps(
            response.raw_response or {}, ensure_ascii=False, default=str
        )

        for r in response.results:
            rid = uuid.uuid4().hex
            await self.repo.create_result(
                result_id=rid,
                task_id=task.task_id,
                user_id=task.user_id,
                image_id=task.image_id,
                skill_id=task.skill_id,
                provider=task.provider,
                result_url=r.url,  # Provider 临时 URL，立即可用
                thumbnail_url=None,
                prompt_used=prompt,
                analysis_json=analysis_json_str,
                provider_response=provider_resp_str,
                favorite=False,
                credits_used=1,
            )
            result_records.append((rid, r.url))

        # 记录模型交互并标记任务成功 —— 用户此刻即可看到结果
        output_urls = [url for _, url in result_records]
        duration_ms = int((time.monotonic() - started_at) * 1000)
        await self._record_interaction(
            task=task,
            image_url=image_url,
            prompt=prompt,
            extra_prompt=task.extra_prompt,
            feedback=feedback,
            options=options,
            status="success",
            output_image_urls=output_urls,
            provider_response=response.raw_response,
            duration_ms=duration_ms,
        )

        # 阶段5：标记任务完成 + 扣减用户积分
        await self.repo.update_task_status(
            task.task_id, status="success", stage="done", progress=100
        )
        # 扣减积分（每次转换消耗 2 积分，非管理员用户）
        stmt = select(User).where(User.user_id == task.user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user and not user.is_admin:
            from app.services.credit_service import CreditService
            credit_service = CreditService(self.db)
            credit_cost = 2
            await credit_service.deduct_credits(
                user_id=task.user_id,
                amount=credit_cost,
                transaction_type="convert_cost",
                description=f"风格转换消耗积分（技能: {task.skill_id}）",
                task_id=task.task_id,
            )
        await self.db.commit()

        # 后台异步：下载结果图 → 上传永久存储 → 生成缩略图 → 替换 URL
        # 使用独立 DB 会话，避免与主会话冲突
        for rid, provider_url in result_records:
            asyncio.create_task(
                self._background_persist_result(
                    user_id=task.user_id,
                    result_id=rid,
                    provider_url=provider_url,
                )
            )

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

        # 实际使用的完整提示词（取首个结果）：前端「重新生成」时回传作为基础提示词
        final_prompt_used = results[0].prompt_used if results else None

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
            final_prompt=final_prompt_used,
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

    async def _record_interaction(
        self,
        *,
        task: StyleTask,
        image_url: str,
        prompt: str,
        extra_prompt: str | None,
        feedback: str | None,
        options: dict,
        status: str,
        output_image_urls: list[str] | None = None,
        provider_response: Any = None,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """
        记录一次与 AI 模型的交互（输入 + 输出），供审计与回溯。

        本方法内部做了异常兜底：即便记录失败也不影响主流程（风格转换任务状态）。
        """
        try:
            rec = ModelInteraction(
                interaction_id=uuid.uuid4().hex,
                task_id=task.task_id,
                user_id=task.user_id,
                skill_id=task.skill_id,
                provider=task.provider,
                input_image_url=image_url,
                prompt_sent=prompt,
                extra_prompt=extra_prompt,
                feedback=feedback,
                location=options.get("location"),
                output_image_urls=json.dumps(output_image_urls or [], ensure_ascii=False),
                output_count=len(output_image_urls or []),
                provider_response=json.dumps(provider_response or {}, ensure_ascii=False, default=str),
                status=status,
                error_message=error_message,
                duration_ms=duration_ms,
            )
            self.db.add(rec)
            await self.db.flush()
        except Exception as exc:
            logger.warning("[交互记录] 写入失败（不影响主流程）: %s", exc)

    @staticmethod
    async def _download(url: str) -> tuple[bytes, str]:
        """异步下载图片字节，返回 (字节流, content_type)，复用连接池。"""
        client = _get_http_client()
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/jpeg")
        return resp.content, content_type

    async def _background_persist_result(
        self, user_id: str, result_id: str, provider_url: str,
    ) -> None:
        """
        后台异步：下载 Provider 临时 URL 的结果图 → 上传到永久存储 → 生成缩略图 → 替换 DB 中的 URL。

        使用独立 DB 会话，避免与主会话冲突。失败不影响用户已看到的结果（临时 URL 仍有 24h+ 有效期）。
        """
        try:
            ext, content_type = await self._probe_content_type(provider_url)

            # 上传原图到永久存储 ‖ 下载+生成缩略图（并行）
            async def _upload_permanent() -> str:
                return await self._fetch_and_store_result(
                    user_id, provider_url, ext, content_type
                )

            async def _download_and_thumb() -> bytes | None:
                try:
                    data, _ = await self._download(provider_url)
                    return await asyncio.to_thread(self.processor.generate_thumbnail, data)
                except Exception as exc:
                    logger.warning("[后台持久化] 缩略图生成失败: %s", exc)
                    return None

            perm_url, thumb_bytes = await asyncio.gather(
                _upload_permanent(), _download_and_thumb()
            )

            # 上传缩略图
            thumb_url = None
            if thumb_bytes is not None:
                thumb_url = await self._upload_result(
                    user_id, thumb_bytes, "jpg", "image/jpeg", prefix="results/thumbnails"
                )

            # 用独立会话更新 DB
            async with async_session_maker() as db:
                from app.repositories.style_repo import StyleRepository
                repo = StyleRepository(db)
                await repo.update_result_urls(result_id, perm_url, thumb_url)
                await db.commit()

            logger.info(
                "[后台持久化] 完成: result_id=%s, perm_url=%s, thumb_url=%s",
                result_id, perm_url, thumb_url,
            )
        except Exception as exc:
            logger.warning(
                "[后台持久化] 失败（临时 URL 仍可用）: result_id=%s, error=%s",
                result_id, exc,
            )

    @staticmethod
    async def _probe_content_type(url: str) -> tuple[str, str]:
        """通过 HEAD 请求探测文件 content-type，避免下载完整文件。返回 (ext, content_type)。"""
        client = _get_http_client()
        try:
            resp = await client.head(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg")
        except Exception:
            content_type = "image/jpeg"
        # 兼容带 charset 的情形
        ct = content_type.split(";")[0].strip().lower()
        ext_map = {
            "image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
            "image/webp": "webp", "image/gif": "gif", "image/bmp": "bmp",
        }
        return ext_map.get(ct, "jpg"), content_type

    def _fetch_and_store_result(
        self, user_id: str, url: str, ext: str, content_type: str,
    ) -> Any:
        """通过 fetch_and_store 直接从远程 URL 存储结果图到对象存储（OSS 走服务端复制）"""
        return asyncio.to_thread(self._do_fetch_and_store, user_id, url, ext, content_type)

    def _do_fetch_and_store(
        self, user_id: str, url: str, ext: str, content_type: str,
    ) -> str:
        """实际执行 fetch_and_store"""
        from app.core.storage import get_storage_provider
        storage = get_storage_provider()
        date = datetime.utcnow().strftime("%Y%m%d")
        key = f"results/{user_id}/{date}/{uuid.uuid4().hex}.{ext}"
        return storage.fetch_and_store(url, key, content_type)

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

    async def _get_reference_images(self, skill_id: str) -> list[str]:
        """
        获取技能的参考图 URL 列表。

        优先级：
        1. 检查内存缓存
        2. 读取 SKILL.md frontmatter 中的 reference_image_url（已上传到 MinIO 的 URL，零上传开销）
        3. 回退：扫描本地 reference-* 文件 → 上传 MinIO → 缓存

        无参考图的技能返回空列表。
        """
        # 1. 检查缓存
        if skill_id in self._reference_image_cache:
            return [self._reference_image_cache[skill_id]]

        # 2. 优先读取 frontmatter 中的已上传 URL
        try:
            config = await self.skill_engine.load_skill_async(skill_id)
            if config.reference_image_url:
                url = config.reference_image_url.strip()
                self._reference_image_cache[skill_id] = url
                logger.info("[参考图] 使用 frontmatter URL: skill=%s, url=%s", skill_id, url)
                return [url]
        except Exception as exc:
            logger.warning("[参考图] 加载 skill 配置失败: %s", exc)

        # 3. 回退：扫描本地文件并上传
        from app.core.skill_engine import SKILLS_DIR
        skill_dir = os.path.join(SKILLS_DIR, skill_id)
        if not os.path.isdir(skill_dir):
            return []

        ref_files: list[str] = []
        for fname in sorted(os.listdir(skill_dir)):
            if fname.startswith("reference-") and any(
                fname.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")
            ):
                ref_files.append(os.path.join(skill_dir, fname))

        if not ref_files:
            return []

        from app.core.storage import get_storage_provider
        storage = get_storage_provider()

        urls: list[str] = []
        for fpath in ref_files:
            ext = os.path.splitext(fpath)[1].lstrip(".")
            content_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

            def _upload(path: str = fpath, e: str = ext, ct: str = content_type) -> str:
                with open(path, "rb") as f:
                    data = f.read()
                key = f"skill-refs/{skill_id}/{os.path.basename(path)}"
                return storage.upload(key, data, ct)

            try:
                url = await asyncio.to_thread(_upload)
                urls.append(url)
                logger.info("[参考图] 上传成功: %s -> %s", fpath, url)
            except Exception as exc:
                logger.warning("[参考图] 上传失败: %s -> %s", fpath, exc)

        if urls:
            self._reference_image_cache[skill_id] = urls[0]

        return urls


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