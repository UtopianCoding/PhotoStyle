"""
IP 贴纸聊天仓储层

封装 ip_chat_sessions / ip_chat_messages / ip_master_templates / ip_sticker_results 的 CRUD。
"""

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ip_chat_message import IPChatMessage
from app.models.ip_chat_session import IPChatSession
from app.models.ip_master_template import IPMasterTemplate
from app.models.ip_sticker_result import IPStickerResult


class IPChatRepository:
    """IP 贴纸聊天仓储"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # -------------------- Session --------------------

    async def create_session(
        self,
        session_id: str,
        user_id: str,
        source_image_id: str | None = None,
    ) -> IPChatSession:
        """创建聊天会话"""
        session = IPChatSession(
            session_id=session_id,
            user_id=user_id,
            source_image_id=source_image_id,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, session_id: str) -> IPChatSession | None:
        """获取会话"""
        stmt = select(IPChatSession).where(IPChatSession.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_session_status(
        self,
        session_id: str,
        status: str,
        current_step: int | None = None,
        source_image_id: str | None = None,
    ) -> None:
        """更新会话状态"""
        values: dict = {"status": status}
        if current_step is not None:
            values["current_step"] = current_step
        if source_image_id is not None:
            values["source_image_id"] = source_image_id
        stmt = (
            update(IPChatSession)
            .where(IPChatSession.session_id == session_id)
            .values(**values)
        )
        await self.db.execute(stmt)

    async def list_sessions(self, user_id: str, limit: int = 20) -> list[IPChatSession]:
        """列出用户的会话（按时间倒序）"""
        stmt = (
            select(IPChatSession)
            .where(IPChatSession.user_id == user_id)
            .order_by(IPChatSession.updated_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # -------------------- Message --------------------

    async def get_next_sequence(self, session_id: str) -> int:
        """获取下一条消息序号"""
        stmt = (
            select(func.coalesce(func.max(IPChatMessage.sequence), 0))
            .where(IPChatMessage.session_id == session_id)
        )
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) + 1

    async def create_message(
        self,
        session_id: str,
        role: str,
        message_type: str,
        content: str | None = None,
        images_json: str | None = None,
        actions_json: str | None = None,
        sequence: int | None = None,
    ) -> IPChatMessage:
        """创建聊天消息"""
        if sequence is None:
            sequence = await self.get_next_sequence(session_id)
        msg = IPChatMessage(
            message_id=uuid.uuid4().hex,
            session_id=session_id,
            role=role,
            message_type=message_type,
            content=content,
            images_json=images_json,
            actions_json=actions_json,
            sequence=sequence,
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def list_messages(
        self, session_id: str, since: int = 0, limit: int = 100
    ) -> list[IPChatMessage]:
        """列出会话消息（按序号正序）"""
        stmt = (
            select(IPChatMessage)
            .where(
                IPChatMessage.session_id == session_id,
                IPChatMessage.sequence > since,
            )
            .order_by(IPChatMessage.sequence.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # -------------------- Master Template --------------------

    async def create_master_template(
        self,
        session_id: str,
        user_id: str,
        master_image_url: str,
        character_prompt: str,
        generation_prompt: str,
        character_description: str | None = None,
        master_thumbnail_url: str | None = None,
    ) -> IPMasterTemplate:
        """创建 IP 母版"""
        template = IPMasterTemplate(
            template_id=uuid.uuid4().hex,
            session_id=session_id,
            user_id=user_id,
            master_image_url=master_image_url,
            master_thumbnail_url=master_thumbnail_url,
            character_prompt=character_prompt,
            character_description=character_description,
            generation_prompt=generation_prompt,
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def get_latest_template(self, session_id: str) -> IPMasterTemplate | None:
        """获取会话最新的母版（最高版本号）"""
        stmt = (
            select(IPMasterTemplate)
            .where(IPMasterTemplate.session_id == session_id)
            .order_by(IPMasterTemplate.version.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def lock_template(self, template_id: str) -> None:
        """锁定母版"""
        stmt = (
            update(IPMasterTemplate)
            .where(IPMasterTemplate.template_id == template_id)
            .values(is_locked=True, locked_at=datetime.utcnow())
        )
        await self.db.execute(stmt)

    async def create_template_version(
        self,
        session_id: str,
        user_id: str,
        master_image_url: str,
        character_prompt: str,
        generation_prompt: str,
        previous_version: int,
        character_description: str | None = None,
        master_thumbnail_url: str | None = None,
    ) -> IPMasterTemplate:
        """创建母版新版本"""
        template = IPMasterTemplate(
            template_id=uuid.uuid4().hex,
            session_id=session_id,
            user_id=user_id,
            master_image_url=master_image_url,
            master_thumbnail_url=master_thumbnail_url,
            character_prompt=character_prompt,
            character_description=character_description,
            generation_prompt=generation_prompt,
            version=previous_version + 1,
        )
        self.db.add(template)
        await self.db.flush()
        return template

    # -------------------- Sticker Result --------------------

    async def create_sticker(
        self,
        session_id: str,
        template_id: str,
        user_id: str,
        sticker_index: int,
        label: str,
        generation_prompt: str,
        result_url: str,
        batch_type: str,
        thumbnail_url: str | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> IPStickerResult:
        """创建贴纸结果"""
        sticker = IPStickerResult(
            sticker_id=uuid.uuid4().hex,
            session_id=session_id,
            template_id=template_id,
            user_id=user_id,
            sticker_index=sticker_index,
            label=label,
            generation_prompt=generation_prompt,
            result_url=result_url,
            thumbnail_url=thumbnail_url,
            status=status,
            batch_type=batch_type,
            error_message=error_message,
        )
        self.db.add(sticker)
        await self.db.flush()
        return sticker

    async def list_stickers(
        self, session_id: str, batch_type: str | None = None
    ) -> list[IPStickerResult]:
        """列出会话的贴纸（按序号正序）"""
        stmt = (
            select(IPStickerResult)
            .where(IPStickerResult.session_id == session_id)
            .order_by(IPStickerResult.sticker_index.asc())
        )
        if batch_type:
            stmt = stmt.where(IPStickerResult.batch_type == batch_type)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def toggle_favorite(self, sticker_id: str, is_favorite: bool) -> None:
        """切换收藏状态"""
        stmt = (
            update(IPStickerResult)
            .where(IPStickerResult.sticker_id == sticker_id)
            .values(is_favorite=is_favorite)
        )
        await self.db.execute(stmt)

    async def increment_redraw(self, sticker_id: str) -> None:
        """重绘次数 +1"""
        sticker = await self.db.get(IPStickerResult, sticker_id)
        if sticker:
            sticker.redraw_count += 1
            await self.db.flush()
