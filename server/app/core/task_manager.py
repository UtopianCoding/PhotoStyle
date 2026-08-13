"""
任务管理器

协调风格转换任务的创建、状态更新、轮询与取消。
任务以异步方式流转：pending -> running -> success / failed / canceled。

注意：本类仅负责任务元数据的状态机管理，真正的 AI 生成由
ProviderManager + StyleService 驱动。
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TaskNotFoundException
from app.models.style_task import StyleTask
from app.repositories.style_repo import StyleRepository


class TaskManager:
    """任务管理器"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = StyleRepository(db)

    @staticmethod
    def generate_task_id() -> str:
        """生成对外任务ID（UUID4）"""
        return uuid.uuid4().hex

    async def create_task(
        self,
        *,
        user_id: str,
        image_id: str,
        skill_id: str,
        provider: str = "qianwen",
        extra_prompt: str | None = None,
        options_json: str | None = None,
    ) -> StyleTask:
        """
        创建一个待执行任务。

        Args:
            user_id: 用户ID
            image_id: 输入图片ID
            skill_id: 技能ID
            provider: AI 提供商
            extra_prompt: 额外提示词
            options_json: 风格选项 JSON 字符串

        Returns:
            创建的 StyleTask 对象
        """
        task = await self.repo.create_task(
            task_id=self.generate_task_id(),
            user_id=user_id,
            image_id=image_id,
            skill_id=skill_id,
            provider=provider,
            extra_prompt=extra_prompt,
            options_json=options_json,
            status="pending",
            stage="queued",
            progress=0,
        )
        return task

    async def update_status(
        self,
        task_id: str,
        *,
        status: str | None = None,
        stage: str | None = None,
        progress: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        provider_task_id: str | None = None,
    ) -> None:
        """
        更新任务状态。

        状态流转时自动补充时间戳：
        - 进入 running 时写入 started_at
        - 进入终态（success/failed/canceled）时写入 completed_at
        """
        task = await self.repo.get_task(task_id)
        if task is None:
            raise TaskNotFoundException(f"任务 [{task_id}] 不存在")

        now = datetime.utcnow()
        started_at = now if status == "running" else None
        completed_at = now if status in ("success", "failed", "canceled") else None

        await self.repo.update_task_status(
            task_id,
            status=status,
            stage=stage,
            progress=progress,
            error_code=error_code,
            error_message=error_message,
            provider_task_id=provider_task_id,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def poll_task(self, task_id: str) -> dict[str, Any]:
        """
        查询任务当前状态。

        Returns:
            状态字典：task_id / status / stage / progress / error
        """
        task = await self.repo.get_task(task_id)
        if task is None:
            raise TaskNotFoundException(f"任务 [{task_id}] 不存在")
        return {
            "task_id": task.task_id,
            "status": task.status,
            "stage": task.stage,
            "progress": task.progress,
            "error": task.error_message,
            "provider_task_id": task.provider_task_id,
        }

    async def cancel_task(self, task_id: str) -> StyleTask:
        """
        取消任务。

        仅当任务处于 pending / running 时可取消；已终态的任务保持原样。
        注意：此方法仅更新本地任务状态，不保证能取消远端 AI 任务。
        """
        task = await self.repo.get_task(task_id)
        if task is None:
            raise TaskNotFoundException(f"任务 [{task_id}] 不存在")

        if task.status in ("pending", "running"):
            await self.repo.update_task_status(
                task_id,
                status="canceled",
                stage="canceled",
                progress=task.progress,
                completed_at=datetime.utcnow(),
            )
            # 刷新以获取最新状态
            await self.db.refresh(task)
        return task
