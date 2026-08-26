"""
3D 翻页画册服务

提供画册的创建、查询、更新和删除功能。
创建画册时，根据用户选择的转换结果图片自动生成画册页面。
"""

import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.flipbook import FlipbookPage, FlipbookProject
from app.models.style_result import StyleResult
from app.schemas.flipbook import (
    CreateFlipbookRequest,
    FlipbookListResponse,
    FlipbookPageRead,
    FlipbookProjectBrief,
    FlipbookProjectRead,
)

logger = logging.getLogger(__name__)


class FlipbookService:
    """3D 翻页画册服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_flipbook(
        self, user_id: str, request: CreateFlipbookRequest
    ) -> FlipbookProjectRead:
        """
        创建画册项目。

        流程：
        1. 根据 result_ids 查询转换结果
        2. 创建画册项目记录（状态为 creating，页面先按选择顺序创建）
        3. 在后台触发 AI 任务：排序照片（时间线/故事叙事）→ 生成主题和 caption
        4. 立即返回，前端轮询状态直到 ready
        """
        import asyncio

        project_id = f"fb_{uuid.uuid4().hex[:16]}"

        # 查询转换结果
        results = await self._get_style_results(user_id, request.result_ids)
        if not results:
            raise NotFoundException("未找到有效的转换结果")

        # 创建项目（状态为 creating）
        project = FlipbookProject(
            project_id=project_id,
            user_id=user_id,
            title=request.title,
            kicker=request.kicker,
            status="creating",  # 初始状态为 creating，AI 排序+分析完成后变为 ready
            page_count=len(results),
            source_image_ids=json.dumps(request.result_ids),
            cover_url=results[0].result_url if results else None,
        )
        self.db.add(project)
        await self.db.flush()

        # 创建页面（先按选择顺序；后台 AI 任务会重新排序并更新 page_order）
        pages: list[FlipbookPage] = []
        for idx, r in enumerate(results):
            page_id = f"page_{idx + 1:02d}"
            page = FlipbookPage(
                project_id=project_id,
                page_id=page_id,
                page_order=idx,
                image_url=r.result_url,
                source_image_id=r.image_id,
                image_width=None,
                image_height=None,
                alt=r.image_id,
                caption=None,  # AI 分析后填充
                text=None,
                fit=None,
            )
            self.db.add(page)
            pages.append(page)

        await self.db.commit()
        await self.db.refresh(project)

        # 在后台启动 AI 分析任务
        asyncio.create_task(self._run_ai_analysis(project_id))
        logger.info(f"[Flipbook] 画册创建成功，AI 分析已启动: {project_id}")

        # 构造响应
        return FlipbookProjectRead(
            project_id=project.project_id,
            title=project.title,
            kicker=project.kicker,
            status=project.status,
            cover_url=project.cover_url,
            theme_json=project.theme_json,
            page_count=project.page_count,
            error_message=project.error_message,
            pages=[
                FlipbookPageRead(
                    page_id=p.page_id,
                    page_order=p.page_order,
                    image_url=p.image_url,
                    source_image_id=p.source_image_id,
                    image_width=p.image_width,
                    image_height=p.image_height,
                    alt=p.alt,
                    caption=p.caption,
                    text=p.text,
                    fit=p.fit,
                )
                for p in pages
            ],
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def _run_ai_analysis(self, project_id: str) -> None:
        """后台运行 AI 分析任务"""
        from app.database import get_db
        from app.services.flipbook_ai_service import FlipbookAIService

        try:
            async for db in get_db():
                ai_service = FlipbookAIService(db)
                await ai_service.analyze_and_enhance(project_id)
                break
        except Exception as e:
            logger.error(f"[Flipbook] AI 分析任务失败: {e}", exc_info=True)

    async def get_flipbook(self, user_id: str, project_id: str) -> FlipbookProjectRead:
        """获取画册详情"""
        project = await self._get_project(project_id)
        if project is None:
            raise NotFoundException(f"画册 [{project_id}] 不存在")
        if project.user_id != user_id:
            raise ForbiddenException("无权访问该画册")

        # 查询页面
        result = await self.db.execute(
            select(FlipbookPage)
            .where(FlipbookPage.project_id == project_id)
            .order_by(FlipbookPage.page_order)
        )
        pages = list(result.scalars().all())

        return FlipbookProjectRead(
            project_id=project.project_id,
            title=project.title,
            kicker=project.kicker,
            status=project.status,
            cover_url=project.cover_url,
            theme_json=project.theme_json,
            page_count=project.page_count,
            error_message=project.error_message,
            pages=[
                FlipbookPageRead(
                    page_id=p.page_id,
                    page_order=p.page_order,
                    image_url=p.image_url,
                    source_image_id=p.source_image_id,
                    image_width=p.image_width,
                    image_height=p.image_height,
                    alt=p.alt,
                    caption=p.caption,
                    text=p.text,
                    fit=p.fit,
                )
                for p in pages
            ],
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def list_flipbooks(
        self, user_id: str, page: int = 1, page_size: int = 20
    ) -> FlipbookListResponse:
        """分页获取用户画册列表"""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size

        # 查询总数
        count_result = await self.db.execute(
            select(func.count())
            .select_from(FlipbookProject)
            .where(FlipbookProject.user_id == user_id)
        )
        total = count_result.scalar_one()

        # 查询列表
        result = await self.db.execute(
            select(FlipbookProject)
            .where(FlipbookProject.user_id == user_id)
            .order_by(FlipbookProject.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        projects = list(result.scalars().all())

        return FlipbookListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[
                FlipbookProjectBrief(
                    project_id=p.project_id,
                    title=p.title,
                    kicker=p.kicker,
                    status=p.status,
                    cover_url=p.cover_url,
                    page_count=p.page_count,
                    created_at=p.created_at,
                )
                for p in projects
            ],
        )

    async def delete_flipbook(self, user_id: str, project_id: str) -> bool:
        """删除画册及其页面"""
        project = await self._get_project(project_id)
        if project is None:
            raise NotFoundException(f"画册 [{project_id}] 不存在")
        if project.user_id != user_id:
            raise ForbiddenException("无权删除该画册")

        # 先删除页面
        await self.db.execute(
            delete(FlipbookPage).where(FlipbookPage.project_id == project_id)
        )
        # 再删除项目
        await self.db.delete(project)
        await self.db.commit()
        return True

    async def update_page(
        self,
        user_id: str,
        project_id: str,
        page_id: str,
        caption: str | None = None,
        text: str | None = None,
        fit: str | None = None,
    ) -> FlipbookPageRead:
        """更新画册页面信息"""
        project = await self._get_project(project_id)
        if project is None:
            raise NotFoundException(f"画册 [{project_id}] 不存在")
        if project.user_id != user_id:
            raise ForbiddenException("无权修改该画册")

        result = await self.db.execute(
            select(FlipbookPage).where(
                FlipbookPage.project_id == project_id,
                FlipbookPage.page_id == page_id,
            )
        )
        page = result.scalar_one_or_none()
        if page is None:
            raise NotFoundException(f"页面 [{page_id}] 不存在")

        if caption is not None:
            page.caption = caption
        if text is not None:
            page.text = text
        if fit is not None:
            page.fit = fit

        await self.db.commit()
        await self.db.refresh(page)

        return FlipbookPageRead(
            page_id=page.page_id,
            page_order=page.page_order,
            image_url=page.image_url,
            source_image_id=page.source_image_id,
            image_width=page.image_width,
            image_height=page.image_height,
            alt=page.alt,
            caption=page.caption,
            text=page.text,
            fit=page.fit,
        )

    async def regenerate_flipbook(
        self, user_id: str, project_id: str
    ) -> FlipbookProjectRead:
        """
        重新生成画册的 AI 内容（主题和 caption）。

        保留原有页面图片，仅重新调用 AI 分析生成主题色和 caption。
        """
        import asyncio

        project = await self._get_project(project_id)
        if project is None:
            raise NotFoundException(f"画册 [{project_id}] 不存在")
        if project.user_id != user_id:
            raise ForbiddenException("无权操作该画册")

        # 重置状态为 creating，清空旧的 AI 生成内容
        project.status = "creating"
        project.theme_json = None
        project.error_message = None

        # 清空所有页面的 caption（保留图片）
        result = await self.db.execute(
            select(FlipbookPage).where(FlipbookPage.project_id == project_id)
        )
        pages = list(result.scalars().all())
        for page in pages:
            page.caption = None

        await self.db.commit()
        await self.db.refresh(project)

        # 在后台重新启动 AI 分析
        asyncio.create_task(self._run_ai_analysis(project_id))
        logger.info(f"[Flipbook] 画册重新生成已启动: {project_id}")

        return FlipbookProjectRead(
            project_id=project.project_id,
            title=project.title,
            kicker=project.kicker,
            status=project.status,
            cover_url=project.cover_url,
            theme_json=project.theme_json,
            page_count=project.page_count,
            error_message=project.error_message,
            pages=[
                FlipbookPageRead(
                    page_id=p.page_id,
                    page_order=p.page_order,
                    image_url=p.image_url,
                    source_image_id=p.source_image_id,
                    image_width=p.image_width,
                    image_height=p.image_height,
                    alt=p.alt,
                    caption=p.caption,
                    text=p.text,
                    fit=p.fit,
                )
                for p in pages
            ],
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def list_available_photos(self, user_id: str, limit: int = 200) -> list[dict]:
        """
        获取用户所有可用的转换结果照片。

        直接查询 style_results 表，返回每张结果图的信息。
        """
        result = await self.db.execute(
            select(StyleResult)
            .where(StyleResult.user_id == user_id)
            .order_by(StyleResult.created_at.desc())
            .limit(limit)
        )
        results = list(result.scalars().all())

        photos = []
        for r in results:
            url = r.result_url
            if not url:
                continue
            photos.append({
                "resultId": r.result_id,
                "resultUrl": url,
                "thumbnailUrl": r.thumbnail_url or url,
                "taskId": r.task_id,
                "imageId": r.image_id,
                "provider": r.provider,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            })
        return photos

    # -------------------- 内部方法 --------------------

    async def _get_project(self, project_id: str) -> FlipbookProject | None:
        """根据 project_id 获取项目"""
        result = await self.db.execute(
            select(FlipbookProject).where(FlipbookProject.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def _get_style_results(
        self, user_id: str, result_ids: list[str]
    ) -> list[StyleResult]:
        """
        根据结果ID列表获取转换结果。
        只返回属于当前用户的结果，按传入顺序排列。
        """
        if not result_ids:
            return []

        result = await self.db.execute(
            select(StyleResult).where(
                StyleResult.user_id == user_id,
                StyleResult.result_id.in_(result_ids),
            )
        )
        rows = list(result.scalars().all())

        # 按传入顺序排列
        id_to_row = {r.result_id: r for r in rows}
        return [id_to_row[rid] for rid in result_ids if rid in id_to_row]
