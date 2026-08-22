"""
IP 贴纸聊天编排服务

管理多轮对话状态机：
  awaiting_photo → generating_base → reviewing_base
  → generating_test → reviewing_test → generating_batch
  → previewing → selecting → completed

编排消息持久化、AI 生成调度、WebSocket 推送。
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AppException,
    ForbiddenException,
    ValidationException,
)
from app.database import async_session_maker
from app.models.ip_master_template import IPMasterTemplate
from app.models.user import User
from app.repositories.ip_chat_repo import IPChatRepository
from app.services.ip_sticker_gen_service import IPStickerGenService

logger = logging.getLogger(__name__)


# WebSocket 发送锁（防止并发写入导致连接异常）
_ws_send_locks: dict[str, asyncio.Lock] = {}


def _get_ws_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _ws_send_locks:
        _ws_send_locks[session_id] = asyncio.Lock()
    return _ws_send_locks[session_id]


class IPStickerChatService:
    """IP 贴纸聊天编排服务"""

    def __init__(self, db: AsyncSession, ws: WebSocket, user: User) -> None:
        self.db = db
        self.ws = ws
        self.user = user
        self.repo = IPChatRepository(db)
        self.session_id: str | None = None
        self._cancel_event = asyncio.Event()
        self._gen_task: asyncio.Task | None = None
        self._connected = True

    # ================================================================
    # 会话生命周期
    # ================================================================

    async def create_session(self) -> str:
        """创建新会话"""
        session_id = uuid.uuid4().hex
        await self.repo.create_session(session_id, self.user.user_id)
        await self.db.commit()
        self.session_id = session_id

        await self._send("session_created", {
            "session_id": session_id,
            "status": "awaiting_photo",
            "step": 0,
        })
        await self._send_text(
            "你好！我是你的 IP 表情包设计师 🎨\n\n"
            "我会帮你把照片变成专属的 Q 版表情包。\n\n"
            "第一步，请上传一张你最喜欢的、能清楚看到脸型、发型和配饰的照片。"
        )
        return session_id

    async def resume_session(self, session_id: str) -> None:
        """恢复已有会话，加载历史消息"""
        session = await self.repo.get_session(session_id)
        if not session:
            raise ValidationException("会话不存在")
        if session.user_id != self.user.user_id:
            raise ForbiddenException("无权访问该会话")

        self.session_id = session_id

        # 加载历史消息
        messages = await self.repo.list_messages(session_id, limit=500)
        history = []
        for msg in messages:
            item: dict[str, Any] = {
                "message_id": msg.message_id,
                "role": msg.role,
                "message_type": msg.message_type,
                "content": msg.content,
                "sequence": msg.sequence,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            if msg.images_json:
                try:
                    item["images"] = json.loads(msg.images_json)
                except Exception:
                    item["images"] = []
            if msg.actions_json:
                try:
                    item["actions"] = json.loads(msg.actions_json)
                except Exception:
                    item["actions"] = []
            history.append(item)

        # 加载母版
        template = await self.repo.get_latest_template(session_id)
        template_data = None
        if template:
            template_data = {
                "template_id": template.template_id,
                "master_image_url": template.master_image_url,
                "character_description": template.character_description,
                "version": template.version,
                "is_locked": template.is_locked,
            }

        await self._send("session_resumed", {
            "session_id": session_id,
            "status": session.status,
            "step": session.current_step,
            "history": history,
            "master_template": template_data,
        })

    async def on_disconnect(self) -> None:
        """WebSocket 断开"""
        self._connected = False
        self._cancel_event.set()
        if self._gen_task and not self._gen_task.done():
            self._gen_task.cancel()
        if self.session_id:
            _ws_send_locks.pop(self.session_id, None)

    # ================================================================
    # 消息分发
    # ================================================================

    async def handle_message(self, raw: dict) -> None:
        """路由客户端消息到对应处理器"""
        msg_type = raw.get("type", "")
        payload = raw.get("payload", {})
        request_id = raw.get("request_id")

        # 延迟创建会话：收到第一条消息时才创建后端 session
        if not self.session_id:
            await self.create_session()

        handlers: dict[str, Any] = {
            "set_photo": self._handle_set_photo,
            "chat": self._handle_chat,
            "confirm_base": self._handle_confirm_base,
            "modify_base": self._handle_modify_base,
            "approve_test": self._handle_approve_test,
            "regenerate_test": self._handle_regenerate_test,
            "generate_full": self._handle_approve_test,
            "redraw_sticker": self._handle_redraw_sticker,
            "toggle_favorite": self._handle_toggle_favorite,
        }

        handler = handlers.get(msg_type)
        if not handler:
            await self._send_error(f"未知消息类型: {msg_type}", request_id)
            return

        try:
            await handler(payload, request_id)
        except AppException as exc:
            await self._send_error(exc.message, request_id)
        except Exception as exc:
            logger.exception("[IP贴纸] 处理消息异常: type=%s", msg_type)
            await self._send_error(f"服务器内部错误: {exc}", request_id)

    # ================================================================
    # Step 0: 设置照片 → 生成 IP 母版
    # ================================================================

    async def _handle_set_photo(self, payload: dict, req_id: str | None) -> None:
        """用户设置源图片，触发 IP 母版生成"""
        image_id = payload.get("image_id")
        if not image_id:
            raise ValidationException("请提供图片ID")

        # 校验图片归属
        from app.models.image import Image
        from sqlalchemy import select
        stmt = select(Image).where(Image.image_id == image_id)
        result = await self.db.execute(stmt)
        image = result.scalar_one_or_none()
        if not image:
            raise ValidationException("图片不存在")
        if image.user_id != self.user.user_id:
            raise ForbiddenException("无权使用该图片")

        # 更新会话
        await self.repo.update_session_status(
            self.session_id, "generating_base", current_step=1,
            source_image_id=image_id,
        )
        await self.db.commit()

        # 保存用户消息
        await self._save_message(
            role="user", message_type="image_single",
            images_json=json.dumps([{"url": image.original_url, "label": "上传的照片"}]),
        )

        # 回复
        await self._send_text(
            "收到照片！正在为你生成 Q 版 IP 母版形象，大约需要 30-60 秒 ⏳"
        )
        await self._send_image_generating("正在生成 IP 母版...")
        await self._send_state_changed("generating_base", 1)

        # 后台生成（不阻塞 WS）
        image_url = image.original_url
        self._gen_task = asyncio.create_task(
            self._bg_generate_base(image_url, req_id)
        )

    async def _bg_generate_base(self, image_url: str, req_id: str | None) -> None:
        """后台任务：生成 IP 母版"""
        async with async_session_maker() as db:
            try:
                gen_service = IPStickerGenService(db)
                repo = IPChatRepository(db)

                result = await gen_service.generate_base_image(
                    user_id=self.user.user_id,
                    session_id=self.session_id,
                    image_url=image_url,
                )

                # 创建母版记录
                template = await repo.create_master_template(
                    session_id=self.session_id,
                    user_id=self.user.user_id,
                    master_image_url=result["image_url"],
                    character_prompt=result["character_prompt"],
                    character_description=result.get("character_description"),
                    generation_prompt=result["generation_prompt"],
                    master_thumbnail_url=result.get("thumbnail_url"),
                )

                # 更新会话状态
                await repo.update_session_status(
                    self.session_id, "reviewing_base", current_step=2,
                )
                await db.commit()

                # 推送结果
                await self._save_and_send_image(
                    images=[{
                        "url": result["image_url"],
                        "thumbnail_url": result.get("thumbnail_url"),
                        "template_id": template.template_id,
                    }],
                    message=(
                        "这是为你生成的 IP 母版形象 ✨\n\n"
                        f"角色特征：{result.get('character_description', '')}\n\n"
                        "请查看是否满意？确认后我会用这个形象制作整套表情包。"
                    ),
                    actions=[
                        {"action": "confirm_base", "label": "满意，确认母版", "type": "primary"},
                        {"action": "modify_base", "label": "我要修改", "type": "default"},
                    ],
                )
                await self._send_state_changed("reviewing_base", 2)

            except Exception as exc:
                logger.exception("[IP贴纸] 母版生成失败: %s", exc)
                await self._send_error(f"IP 母版生成失败: {exc}", req_id)
                async with async_session_maker() as db2:
                    repo2 = IPChatRepository(db2)
                    await repo2.update_session_status(
                        self.session_id, "reviewing_base", current_step=2,
                    )
                    await db2.commit()

    # ================================================================
    # Step 2: 确认 / 修改母版
    # ================================================================

    async def _handle_confirm_base(self, payload: dict, req_id: str | None) -> None:
        """确认 IP 母版，进入测试贴纸生成"""
        template = await self.repo.get_latest_template(self.session_id)
        if not template:
            raise ValidationException("尚未生成 IP 母版")

        await self.repo.lock_template(template.template_id)
        await self.repo.update_session_status(
            self.session_id, "generating_test", current_step=3,
        )
        await self.db.commit()

        await self._save_message(
            role="user", message_type="text",
            content="确认母版，开始生成测试贴纸",
        )
        await self._send_text(
            "母版已锁定 🔒 正在生成 4 张测试贴纸检验一致性，大约需要 1-2 分钟..."
        )
        await self._send_image_generating("正在生成测试贴纸（4 张）...")
        await self._send_state_changed("generating_test", 3)

        # 后台生成测试贴纸
        self._gen_task = asyncio.create_task(
            self._bg_generate_test_stickers(template, req_id)
        )

    async def _handle_modify_base(self, payload: dict, req_id: str | None) -> None:
        """用户要求修改母版"""
        feedback = payload.get("text", "").strip()
        if not feedback:
            await self._send_text(
                "请告诉我你想修改什么？比如：\n"
                "- 发型换成短发\n- 不要眼镜\n- 脸型瘦一点\n- 换成彩色风格"
            )
            return

        template = await self.repo.get_latest_template(self.session_id)
        if not template:
            raise ValidationException("尚未生成 IP 母版")

        await self.repo.update_session_status(
            self.session_id, "generating_base", current_step=1,
        )
        await self.db.commit()

        await self._save_message(
            role="user", message_type="text", content=f"修改意见：{feedback}"
        )
        await self._send_text(f"收到！正在根据你的意见重新生成母版，大约需要 30-60 秒 ⏳")
        await self._send_image_generating("正在重新生成 IP 母版...")

        # 获取源图 URL
        from app.models.image import Image
        from sqlalchemy import select
        session = await self.repo.get_session(self.session_id)
        stmt = select(Image).where(Image.image_id == session.source_image_id)
        result = await self.db.execute(stmt)
        image = result.scalar_one_or_none()
        if not image:
            raise ValidationException("源图片不存在")

        self._gen_task = asyncio.create_task(
            self._bg_regenerate_base(
                image.original_url, feedback, template, req_id
            )
        )

    async def _bg_regenerate_base(
        self,
        image_url: str,
        feedback: str,
        previous_template: IPMasterTemplate,
        req_id: str | None,
    ) -> None:
        """后台任务：修改后重新生成母版"""
        async with async_session_maker() as db:
            try:
                gen_service = IPStickerGenService(db)
                repo = IPChatRepository(db)

                result = await gen_service.generate_base_image(
                    user_id=self.user.user_id,
                    session_id=self.session_id,
                    image_url=image_url,
                    modification_feedback=feedback,
                    previous_template=previous_template,
                )

                template = await repo.create_template_version(
                    session_id=self.session_id,
                    user_id=self.user.user_id,
                    master_image_url=result["image_url"],
                    character_prompt=result["character_prompt"],
                    character_description=result.get("character_description"),
                    generation_prompt=result["generation_prompt"],
                    previous_version=previous_template.version,
                    master_thumbnail_url=result.get("thumbnail_url"),
                )

                await repo.update_session_status(
                    self.session_id, "reviewing_base", current_step=2,
                )
                await db.commit()

                await self._save_and_send_image(
                    images=[{
                        "url": result["image_url"],
                        "thumbnail_url": result.get("thumbnail_url"),
                        "template_id": template.template_id,
                    }],
                    message=(
                        f"这是修改后的 IP 母版（V{template.version}）✨\n\n"
                        f"角色特征：{result.get('character_description', '')}\n\n"
                        "满意吗？确认后即可开始制作表情包。"
                    ),
                    actions=[
                        {"action": "confirm_base", "label": "满意，确认母版", "type": "primary"},
                        {"action": "modify_base", "label": "继续修改", "type": "default"},
                    ],
                )
                await self._send_state_changed("reviewing_base", 2)

            except Exception as exc:
                logger.exception("[IP贴纸] 母版修改失败: %s", exc)
                await self._send_error(f"母版修改失败: {exc}", req_id)

    # ================================================================
    # Step 3: 测试贴纸（一致性校验）
    # ================================================================

    async def _bg_generate_test_stickers(
        self, template: IPMasterTemplate, req_id: str | None
    ) -> None:
        """后台任务：生成 4 张测试贴纸"""
        async with async_session_maker() as db:
            try:
                gen_service = IPStickerGenService(db)
                repo = IPChatRepository(db)

                # 4 个测试动作
                test_configs = [
                    {"index": 1, "label": "开心/好耶",
                     "prompt_suffix": "jumping with both arms raised high, very happy excited face"},
                    {"index": 2, "label": "疑惑/不理解",
                     "prompt_suffix": "tilting head with hand on chin, confused expression, question mark floating"},
                    {"index": 3, "label": "疲惫/累趴了",
                     "prompt_suffix": "lying face down on desk, exhausted, ZZZ symbols floating above"},
                    {"index": 4, "label": "加油/冲冲冲",
                     "prompt_suffix": "running forward energetically, hair blowing back, determined expression"},
                ]

                results = await gen_service.generate_sticker_batch(
                    user_id=self.user.user_id,
                    session_id=self.session_id,
                    template=template,
                    sticker_configs=test_configs,
                    batch_type="test_batch",
                )
                await db.commit()

                await repo.update_session_status(
                    self.session_id, "reviewing_test", current_step=3,
                )
                await db.commit()

                # 推送结果
                images = []
                for r in results:
                    images.append({
                        "sticker_id": r.get("sticker_id"),
                        "url": r.get("url", ""),
                        "thumbnail_url": r.get("thumbnail_url"),
                        "index": r["index"],
                        "label": r["label"],
                        "status": r["status"],
                    })

                await self._save_and_send_image_grid(
                    images=images,
                    grid_type="test",
                    message=(
                        "4 张测试贴纸生成完成！请检查角色一致性：\n"
                        "• 脸型、发型是否一致？\n"
                        "• 眼镜/配饰是否相同？\n"
                        "• 画风是否统一？\n\n"
                        "确认一致后，请选择要生成的表情包数量（4/8/12/20张）。"
                    ),
                    actions=[
                        {"action": "approve_test", "label": "生成 4 张", "type": "primary", "payload": {"count": 4}},
                        {"action": "approve_test", "label": "生成 8 张", "type": "primary", "payload": {"count": 8}},
                        {"action": "approve_test", "label": "生成 12 张", "type": "primary", "payload": {"count": 12}},
                        {"action": "approve_test", "label": "生成 20 张", "type": "default", "payload": {"count": 20}},
                        {"action": "regenerate_test", "label": "重新生成测试贴纸", "type": "default"},
                    ],
                )
                await self._send_state_changed("reviewing_test", 3)

            except Exception as exc:
                logger.exception("[IP贴纸] 测试贴纸生成失败: %s", exc)
                await self._send_error(f"测试贴纸生成失败: {exc}", req_id)

    async def _handle_approve_test(self, payload: dict, req_id: str | None) -> None:
        """测试贴纸通过，按用户选择的数量生成表情包"""
        template = await self.repo.get_latest_template(self.session_id)
        if not template:
            raise ValidationException("母版不存在")

        count = int(payload.get("count", 20))
        if count not in (4, 8, 12, 20):
            count = 20

        await self.repo.update_session_status(
            self.session_id, "generating_batch", current_step=4,
        )
        await self.db.commit()

        await self._save_message(
            role="user", message_type="text",
            content=f"一致性通过，生成 {count} 张表情包",
        )
        await self._send_text(
            f"太好了！正在生成 {count} 张表情包，大约需要 {count * 10 // 60 + 1}-{count * 15 // 60 + 2} 分钟 🎉"
        )
        await self._send_image_generating(f"正在生成表情包（{count} 张）...")
        await self._send_state_changed("generating_batch", 4)

        self._gen_task = asyncio.create_task(
            self._bg_generate_full_batch(template, req_id, count)
        )

    async def _handle_regenerate_test(self, payload: dict, req_id: str | None) -> None:
        """重新生成测试贴纸"""
        template = await self.repo.get_latest_template(self.session_id)
        if not template:
            raise ValidationException("母版不存在")

        await self.repo.update_session_status(
            self.session_id, "generating_test", current_step=3,
        )
        await self.db.commit()

        await self._send_text("正在重新生成测试贴纸...")
        await self._send_image_generating("正在重新生成测试贴纸（4 张）...")

        self._gen_task = asyncio.create_task(
            self._bg_generate_test_stickers(template, req_id)
        )

    async def _bg_generate_full_batch(
        self, template: IPMasterTemplate, req_id: str | None, count: int = 20
    ) -> None:
        """后台任务：生成指定数量的贴纸"""
        async with async_session_maker() as db:
            try:
                gen_service = IPStickerGenService(db)
                repo = IPChatRepository(db)

                # 完整 20 个表情（按需截取）
                full_configs = [
                    {"index": 1, "label": "收到", "prompt_suffix": "saluting with one hand, determined expression"},
                    {"index": 2, "label": "好的", "prompt_suffix": "giving OK hand gesture, cheerful nod"},
                    {"index": 3, "label": "没问题", "prompt_suffix": "arms crossed confidently, big grin, thumbs up"},
                    {"index": 4, "label": "我可以", "prompt_suffix": "giving thumbs up with confident wink"},
                    {"index": 5, "label": "等一下", "prompt_suffix": "one palm forward in stop gesture, serious expression"},
                    {"index": 6, "label": "好耶", "prompt_suffix": "jumping with both arms raised high, very excited"},
                    {"index": 7, "label": "爱了爱了", "prompt_suffix": "hands on cheeks with heart eyes, blushing"},
                    {"index": 8, "label": "不理解", "prompt_suffix": "tilting head with question mark floating above"},
                    {"index": 9, "label": "太难了", "prompt_suffix": "holding head in despair, sweat drops falling"},
                    {"index": 10, "label": "人间蒸发", "prompt_suffix": "body dissolving into dotted lines, fading away"},
                    {"index": 11, "label": "我超猛", "prompt_suffix": "flexing muscles with both arms, confident powerful face"},
                    {"index": 12, "label": "冲冲冲", "prompt_suffix": "running forward energetically, hair blowing back"},
                    {"index": 13, "label": "拿捏", "prompt_suffix": "confident smirk, adjusting glasses with one finger"},
                    {"index": 14, "label": "累趴了", "prompt_suffix": "lying face down on desk, exhausted, ZZZ symbols"},
                    {"index": 15, "label": "辛苦了", "prompt_suffix": "offering a hot drink with both hands, warm smile"},
                    {"index": 16, "label": "谢谢你", "prompt_suffix": "hands together bowing slightly, grateful expression"},
                    {"index": 17, "label": "对不起", "prompt_suffix": "hands together with apologetic pout, small tear drop"},
                    {"index": 18, "label": "在吗", "prompt_suffix": "peeking from the side, waving one hand, curious look"},
                    {"index": 19, "label": "早上好", "prompt_suffix": "waving cheerfully, small sun icon beside head"},
                    {"index": 20, "label": "晚安", "prompt_suffix": "sleeping on pillow, peaceful face, moon and stars"},
                ][:count]  # 按用户选择的数量截取

                results = await gen_service.generate_sticker_batch(
                    user_id=self.user.user_id,
                    session_id=self.session_id,
                    template=template,
                    sticker_configs=full_configs,
                    batch_type="full_batch",
                )
                await db.commit()

                await repo.update_session_status(
                    self.session_id, "previewing", current_step=5,
                )
                await db.commit()

                images = []
                for r in results:
                    images.append({
                        "sticker_id": r.get("sticker_id"),
                        "url": r.get("url", ""),
                        "thumbnail_url": r.get("thumbnail_url"),
                        "index": r["index"],
                        "label": r["label"],
                        "status": r["status"],
                    })

                await self._save_and_send_image_grid(
                    images=images,
                    grid_type="full",
                    message=(
                        "🎉 完整 20 张表情包生成完成！\n\n"
                        "你可以：\n"
                        "• 点击任意贴纸查看大图\n"
                        "• 收藏喜欢的贴纸\n"
                        "• 对不满意的贴纸要求重绘\n"
                        "• 导出整套表情包"
                    ),
                    actions=[
                        {"action": "export_stickers", "label": "导出表情包", "type": "primary"},
                    ],
                )
                await self._send_state_changed("previewing", 5)

            except Exception as exc:
                logger.exception("[IP贴纸] 完整表情包生成失败: %s", exc)
                await self._send_error(f"完整表情包生成失败: {exc}", req_id)

    # ================================================================
    # Step 6: 重绘 / 收藏
    # ================================================================

    async def _handle_redraw_sticker(self, payload: dict, req_id: str | None) -> None:
        """重绘单张贴纸"""
        sticker_id = payload.get("sticker_id")
        feedback = payload.get("text", "").strip()
        if not sticker_id:
            raise ValidationException("请指定要重绘的贴纸")

        template = await self.repo.get_latest_template(self.session_id)
        if not template:
            raise ValidationException("母版不存在")

        # 获取原贴纸信息
        stickers = await self.repo.list_stickers(self.session_id)
        original = None
        for s in stickers:
            if s.sticker_id == sticker_id:
                original = s
                break
        if not original:
            raise ValidationException("贴纸不存在")

        # 判断是否为测试批次贴纸的重绘
        is_test_redraw = original.batch_type == "test_batch"

        await self.repo.increment_redraw(sticker_id)
        await self._save_message(
            role="user", message_type="text",
            content=f"重绘贴纸「{original.label}」" + (f"：{feedback}" if feedback else ""),
        )
        await self._send_text(
            f"正在重绘「{original.label}」..." + ("（将重新生成全部测试贴纸）" if is_test_redraw else "")
        )
        await self._send_image_generating("正在重绘贴纸...")

        if is_test_redraw:
            # 测试贴纸重绘：重新生成全部 4 张测试贴纸，保持四宫格
            await self.repo.update_session_status(
                self.session_id, "generating_test", current_step=3,
            )
            await self.db.commit()
            self._gen_task = asyncio.create_task(
                self._bg_generate_test_stickers(template, req_id)
            )
        else:
            # 正式贴纸重绘：单独重绘
            self._gen_task = asyncio.create_task(
                self._bg_redraw_sticker(template, original, feedback, req_id)
            )

    async def _bg_redraw_sticker(
        self,
        template: IPMasterTemplate,
        original: Any,
        feedback: str,
        req_id: str | None,
    ) -> None:
        """后台任务：重绘单张贴纸"""
        async with async_session_maker() as db:
            try:
                gen_service = IPStickerGenService(db)
                repo = IPChatRepository(db)

                suffix = original.label
                if feedback:
                    suffix = f"{suffix}, {feedback}"

                results = await gen_service.generate_sticker_batch(
                    user_id=self.user.user_id,
                    session_id=self.session_id,
                    template=template,
                    sticker_configs=[{
                        "index": original.sticker_index,
                        "label": original.label,
                        "prompt_suffix": suffix,
                    }],
                    batch_type="redraw",
                )
                await db.commit()

                success_results = [r for r in results if r["status"] == "success"]
                if success_results:
                    r = success_results[0]
                    await self._save_and_send_image(
                        images=[{
                            "url": r["url"],
                            "thumbnail_url": r.get("thumbnail_url"),
                            "sticker_id": r["sticker_id"],
                            "label": r["label"],
                        }],
                        message=f"「{r['label']}」重绘完成！",
                        actions=[
                            {"action": "redraw_sticker", "label": "再改一次", "type": "default",
                             "payload": {"sticker_id": r["sticker_id"]}},
                        ],
                    )
                else:
                    await self._send_error(f"「{original.label}」重绘失败", req_id)

            except Exception as exc:
                logger.exception("[IP贴纸] 贴纸重绘失败: %s", exc)
                await self._send_error(f"贴纸重绘失败: {exc}", req_id)

    async def _handle_toggle_favorite(self, payload: dict, req_id: str | None) -> None:
        """切换贴纸收藏"""
        sticker_id = payload.get("sticker_id")
        is_favorite = payload.get("is_favorite", True)
        if not sticker_id:
            raise ValidationException("请指定贴纸")
        await self.repo.toggle_favorite(sticker_id, bool(is_favorite))
        await self.db.commit()
        await self._send("toggle_favorite_done", {
            "sticker_id": sticker_id,
            "is_favorite": bool(is_favorite),
        }, req_id)

    # ================================================================
    # 自由聊天
    # ================================================================

    async def _handle_chat(self, payload: dict, req_id: str | None) -> None:
        """处理用户自由文本"""
        user_text = payload.get("text", "").strip()
        if not user_text:
            return

        await self._save_message(role="user", message_type="text", content=user_text)

        # 根据当前状态给出引导回复
        session = await self.repo.get_session(self.session_id)
        reply = self._get_guided_reply(session.status, user_text)
        await self._send_text(reply, req_id)

    @staticmethod
    def _get_guided_reply(status: str, user_text: str) -> str:
        """根据当前状态生成引导回复"""
        text_lower = user_text.lower()

        # 通用关键词
        if any(kw in text_lower for kw in ["导出", "下载", "保存"]):
            return (
                "表情包导出功能正在开发中，后续会支持打包下载 PNG 文件。\n"
                "目前你可以右键点击每张贴纸单独保存图片。"
            )

        # 按状态引导
        status_guides = {
            "awaiting_photo": "请先上传一张你的照片，我来帮你生成 Q 版 IP 形象 😊",
            "generating_base": "母版正在生成中，请稍等片刻 ⏳",
            "reviewing_base": "请查看生成的 IP 母版，满意的话点击「确认母版」，不满意可以告诉我修改意见。",
            "generating_test": "测试贴纸正在生成中，请稍等 ⏳",
            "reviewing_test": "请检查测试贴纸的角色一致性，通过后我将生成完整 20 张表情包。",
            "generating_batch": "完整表情包正在生成中，大约需要 3-5 分钟 ⏳",
            "previewing": "表情包已生成！你可以收藏喜欢的贴纸，或对不满意的贴纸要求重绘。",
            "completed": "表情包制作完成！需要我继续扩展更多表情吗？",
        }
        return status_guides.get(status, "有什么需要帮忙的？")

    # ================================================================
    # WebSocket 消息发送
    # ================================================================

    async def _send(self, msg_type: str, payload: dict, request_id: str | None = None) -> None:
        """发送服务端消息（加锁防并发，连接断开时静默跳过）"""
        if not self._connected:
            return
        lock = _get_ws_lock(self.session_id or "")
        async with lock:
            if not self._connected:
                return
            try:
                # 检查 WebSocket 连接状态
                if self.ws.client_state.name != "CONNECTED":
                    self._connected = False
                    return
                await self.ws.send_json({
                    "type": msg_type,
                    "payload": payload,
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except (RuntimeError, Exception) as exc:
                self._connected = False
                logger.debug("[IP贴纸WS] 发送跳过（连接已断开）: %s", exc)

    async def _send_text(self, text: str, request_id: str | None = None) -> None:
        await self._send("chat_reply", {"text": text, "role": "assistant"}, request_id)

    async def _send_image_generating(self, hint: str) -> None:
        await self._send("image_started", {"hint": hint})

    async def _send_state_changed(self, status: str, step: int) -> None:
        await self._send("state_changed", {"status": status, "step": step})

    async def _send_error(self, message: str, request_id: str | None = None) -> None:
        await self._send("error", {"message": message}, request_id)

    async def _save_and_send_image(
        self,
        images: list[dict],
        message: str,
        actions: list[dict] | None = None,
    ) -> None:
        """持久化图片消息并推送"""
        await self._save_message(
            role="assistant",
            message_type="image_single",
            content=message,
            images_json=json.dumps(images, ensure_ascii=False),
            actions_json=json.dumps(actions, ensure_ascii=False) if actions else None,
        )
        payload: dict[str, Any] = {"images": images}
        if message:
            payload["message"] = message
        if actions:
            payload["actions"] = actions
        await self._send("image_completed", payload)

    async def _save_and_send_image_grid(
        self,
        images: list[dict],
        grid_type: str,
        message: str,
        actions: list[dict] | None = None,
    ) -> None:
        """持久化网格消息并推送"""
        await self._save_message(
            role="assistant",
            message_type="image_grid",
            content=message,
            images_json=json.dumps(images, ensure_ascii=False),
            actions_json=json.dumps(actions, ensure_ascii=False) if actions else None,
        )
        await self._send("image_grid_completed", {
            "images": images,
            "grid_type": grid_type,
            "count": len(images),
            "message": message,
            "actions": actions or [],
        })

    async def _save_message(
        self,
        role: str,
        message_type: str,
        content: str | None = None,
        images_json: str | None = None,
        actions_json: str | None = None,
    ) -> None:
        """持久化消息"""
        try:
            async with async_session_maker() as db:
                repo = IPChatRepository(db)
                await repo.create_message(
                    session_id=self.session_id,
                    role=role,
                    message_type=message_type,
                    content=content,
                    images_json=images_json,
                    actions_json=actions_json,
                )
                await db.commit()
        except Exception as exc:
            logger.warning("[IP贴纸] 消息持久化失败: %s", exc)
