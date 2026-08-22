"""
IP 贴纸 REST 辅助路由

提供会话列表、详情、贴纸查询等 HTTP 接口。
WebSocket 用于实时对话，REST 用于辅助查询。
"""

import logging

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.ip_chat_session import IPChatSession
from app.schemas.common import ApiResponse
from app.schemas.ip_sticker import (
    MasterTemplateItem,
    MessageItem,
    SessionDetail,
    SessionItem,
    SessionListResponse,
    StickerItem,
)
from app.repositories.ip_chat_repo import IPChatRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ip-sticker", tags=["IP贴纸"])


@router.get("/sessions", response_model=ApiResponse[SessionListResponse])
async def list_sessions(user: CurrentUser, db: DBSession) -> ApiResponse[SessionListResponse]:
    """列出用户的 IP 贴纸会话"""
    repo = IPChatRepository(db)
    sessions = await repo.list_sessions(user.user_id, limit=20)
    items = [
        SessionItem(
            session_id=s.session_id,
            status=s.status,
            current_step=s.current_step,
            source_image_id=s.source_image_id,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]
    return ApiResponse.success(data=SessionListResponse(sessions=items))


@router.get("/sessions/{session_id}", response_model=ApiResponse[SessionDetail])
async def get_session_detail(
    session_id: str, user: CurrentUser, db: DBSession
) -> ApiResponse[SessionDetail]:
    """获取会话详情（含消息历史、母版、贴纸）"""
    repo = IPChatRepository(db)

    session = await repo.get_session(session_id)
    if not session:
        return ApiResponse.error(message="会话不存在", code=40400)
    if session.user_id != user.user_id:
        return ApiResponse.error(message="无权访问", code=40300)

    # 消息
    messages = await repo.list_messages(session_id, limit=500)
    msg_items = []
    for msg in messages:
        import json
        images = None
        actions = None
        if msg.images_json:
            try:
                images = json.loads(msg.images_json)
            except Exception:
                pass
        if msg.actions_json:
            try:
                actions = json.loads(msg.actions_json)
            except Exception:
                pass
        msg_items.append(MessageItem(
            message_id=msg.message_id,
            role=msg.role,
            message_type=msg.message_type,
            content=msg.content,
            images=images,
            actions=actions,
            sequence=msg.sequence,
            created_at=msg.created_at,
        ))

    # 母版
    template = await repo.get_latest_template(session_id)
    template_item = None
    if template:
        template_item = MasterTemplateItem(
            template_id=template.template_id,
            master_image_url=template.master_image_url,
            master_thumbnail_url=template.master_thumbnail_url,
            character_description=template.character_description,
            version=template.version,
            is_locked=template.is_locked,
            created_at=template.created_at,
        )

    # 贴纸
    stickers = await repo.list_stickers(session_id)
    sticker_items = [
        StickerItem(
            sticker_id=s.sticker_id,
            sticker_index=s.sticker_index,
            label=s.label,
            result_url=s.result_url,
            thumbnail_url=s.thumbnail_url,
            status=s.status,
            batch_type=s.batch_type,
            is_favorite=s.is_favorite,
            redraw_count=s.redraw_count,
            created_at=s.created_at,
        )
        for s in stickers
    ]

    detail = SessionDetail(
        session_id=session.session_id,
        user_id=session.user_id,
        status=session.status,
        current_step=session.current_step,
        source_image_id=session.source_image_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=msg_items,
        master_template=template_item,
        stickers=sticker_items,
    )
    return ApiResponse.success(data=detail)
