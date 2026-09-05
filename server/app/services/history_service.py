"""
历史记录服务

提供风格转换历史列表、详情、收藏、删除与批量删除。
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
    TaskNotFoundException,
)
from app.repositories.style_repo import StyleRepository
from app.schemas.history import HistoryDetail, HistoryItem, HistoryListResponse
from app.schemas.style import TaskResult

logger = logging.getLogger(__name__)


class HistoryService:
    """历史记录服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = StyleRepository(db)

    async def list_history(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        favorite: bool = False,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> HistoryListResponse:
        """分页获取用户历史任务列表；favorite=True 时仅返回含收藏结果的任务"""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size

        tasks = await self.repo.get_history(
            user_id,
            offset=offset,
            limit=page_size,
            favorite=favorite,
            start_date=start_date,
            end_date=end_date,
        )
        total = await self.repo.count_tasks_by_user(
            user_id,
            favorite=favorite,
            start_date=start_date,
            end_date=end_date,
        )

        # 批量查图片 + 批量查结果（消除 N+1，从 50+ 次 SQL 降为 2 次）
        image_ids = list({t.image_id for t in tasks})
        images_map = await self.repo.get_images_map(image_ids)

        task_ids = [t.task_id for t in tasks]
        results_map = await self.repo.get_results_by_tasks(task_ids)

        # 惰性补回：发现缺缩略图的结果则后台生成（避免列表加载原图大 URL）
        try:
            from app.services.thumbnail_backfill import schedule_missing
            schedule_missing([r for rs in results_map.values() for r in rs])
        except Exception:  # noqa: BLE001
            pass

        items: list[HistoryItem] = []
        for task in tasks:
            results = results_map.get(task.task_id, [])
            thumbnails = [r.thumbnail_url or r.result_url for r in results]
            has_favorite = any(r.favorite for r in results)
            image = images_map.get(task.image_id)
            # 多模型模式下 task.provider 为空，从结果中推导实际使用的 Provider 列表
            providers = list({r.provider for r in results if r.provider})
            provider_display = task.provider if task.provider else (providers[0] if providers else "")
            items.append(
                HistoryItem(
                    task_id=task.task_id,
                    skill_id=task.skill_id,
                    provider=provider_display,
                    providers=providers,
                    image_id=task.image_id,
                    original_url=image.original_url if image else "",
                    status=task.status,
                    result_thumbnails=thumbnails,
                    has_favorite=has_favorite,
                    created_at=task.created_at,
                )
            )

        return HistoryListResponse(
            total=total, page=page, page_size=page_size, items=items
        )

    async def detail(self, user_id: str, task_id: str) -> HistoryDetail:
        """获取任务详情（含结果列表）"""
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
                provider=r.provider or "",
                created_at=r.created_at,
            )
            for r in results
        ]

        image = await self.repo.get_image(task.image_id)

        # 多模型模式下 task.provider 为空，从结果中推导
        providers = list({r.provider for r in results if r.provider})
        provider_display = task.provider if task.provider else (providers[0] if providers else "")

        return HistoryDetail(
            task_id=task.task_id,
            user_id=task.user_id,
            skill_id=task.skill_id,
            provider=provider_display,
            providers=providers,
            image_id=task.image_id,
            original_url=image.original_url if image else "",
            extra_prompt=task.extra_prompt,
            status=task.status,
            progress=task.progress,
            results=result_models,
            created_at=task.created_at,
        )

    async def favorite(self, user_id: str, result_id: str, favorite: bool | None = None) -> bool:
        """切换或设置结果收藏状态"""
        result = await self.repo.get_result(result_id)
        if result is None:
            raise NotFoundException(f"结果 [{result_id}] 不存在")
        if result.user_id != user_id:
            raise ForbiddenException("无权操作该结果")
        updated = await self.repo.toggle_favorite(result_id, favorite)
        await self.db.commit()
        return updated.favorite if updated else False

    async def delete(self, user_id: str, task_id: str) -> bool:
        """删除任务及其关联结果"""
        task = await self.repo.get_task(task_id)
        if task is None:
            raise NotFoundException(f"任务 [{task_id}] 不存在")
        if task.user_id != user_id:
            raise ForbiddenException("无权删除该任务")
        ok = await self.repo.delete_task_and_results(task_id)
        await self.db.commit()
        return ok

    async def batch_delete(self, user_id: str, task_ids: list[str]) -> int:
        """批量删除任务及其关联结果（仅删除属于当前用户的任务）"""
        owned: list[str] = []
        for tid in task_ids:
            task = await self.repo.get_task(tid)
            if task and task.user_id == user_id:
                owned.append(tid)
        deleted = await self.repo.batch_delete_tasks(owned)
        await self.db.commit()
        return deleted

    async def remove_results(
        self, user_id: str, task_id: str, result_ids_to_remove: list[str]
    ) -> list[TaskResult]:
        """
        删除指定结果，返回剩余结果列表。

        若删除后任务无剩余结果，则连同任务一并删除并返回空列表。

        Args:
            user_id: 用户 ID
            task_id: 任务 ID
            result_ids_to_remove: 要删除的结果 ID 列表

        Returns:
            剩余的结果列表（TaskResult 格式）；空列表表示任务已整体删除

        Raises:
            NotFoundException: 任务不存在
            ForbiddenException: 无权操作
            ValueError: 参数校验失败
        """
        # 校验任务归属
        task = await self.repo.get_task(task_id)
        if task is None:
            raise TaskNotFoundException(f"任务 [{task_id}] 不存在")
        if task.user_id != user_id:
            raise ForbiddenException("无权操作该任务")

        # 查询该任务下所有结果
        all_results = await self.repo.get_results_by_task(task_id)
        all_result_ids = {r.result_id for r in all_results}

        # 校验要删除的 result_ids 均属于该任务
        invalid_ids = [rid for rid in result_ids_to_remove if rid not in all_result_ids]
        if invalid_ids:
            raise ValueError(f"结果 ID 不属于该任务: {invalid_ids}")

        # 若删除后无剩余结果：整个任务已无意义，连同任务一并删除，返回空列表
        remaining_count = len(all_results) - len(result_ids_to_remove)
        if remaining_count < 1:
            await self.repo.delete_task_and_results(task_id)
            await self.db.commit()
            return []

        # 删除指定结果
        await self.repo.batch_delete(result_ids_to_remove)
        await self.db.commit()

        # 重新查询剩余结果并返回
        remaining_results = await self.repo.get_results_by_task(task_id)
        return [
            TaskResult(
                result_id=r.result_id,
                result_url=r.result_url,
                thumbnail_url=r.thumbnail_url,
                favorite=r.favorite,
                provider=r.provider or "",
                created_at=r.created_at,
            )
            for r in remaining_results
        ]
