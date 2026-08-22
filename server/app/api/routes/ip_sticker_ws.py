"""
IP 贴纸 WebSocket 端点

端点: ws://host/api/v1/ip-sticker/ws?token=<jwt>&session_id=<optional>
"""

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.database import async_session_maker
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.ip_sticker_chat_service import IPStickerChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ip-sticker", tags=["IP贴纸"])


@router.websocket("/ws")
async def ip_sticker_ws(
    websocket: WebSocket,
    token: str = Query(...),
    session_id: str | None = Query(None),
):
    """IP 贴纸制作 WebSocket 连接"""
    # 1. JWT 鉴权 + 获取用户对象
    user = None
    async with async_session_maker() as db:
        try:
            auth_service = AuthService(db)
            payload = auth_service.verify_token(token, expected_type="access")
            user_id = payload.get("sub")
            if not user_id:
                await websocket.close(code=4001, reason="Token 无效")
                return
        except Exception as exc:
            logger.warning("[IP贴纸WS] JWT 鉴权失败: %s", exc)
            await websocket.close(code=4001, reason="Token 无效")
            return

        from sqlalchemy import select
        stmt = select(User).where(User.user_id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            await websocket.close(code=4001, reason="用户不存在")
            return

    # 3. Accept 连接
    await websocket.accept()
    logger.info("[IP贴纸WS] 连接已接受: user_id=%s, session_id=%s", user_id, session_id)

    # 4. 创建聊天服务
    async with async_session_maker() as db:
        chat_service = IPStickerChatService(db, websocket, user)

        try:
            # 仅恢复已有会话（有 session_id 时），不自动创建新会话
            if session_id:
                await chat_service.resume_session(session_id)

            # 消息主循环
            while True:
                try:
                    raw = await websocket.receive_json()
                    # 每条消息前检查连接状态
                    if websocket.client_state.name != "CONNECTED":
                        break
                    await chat_service.handle_message(raw)
                except WebSocketDisconnect:
                    raise
                except RuntimeError as exc:
                    # WebSocket 状态异常（not connected / close sent）
                    logger.info("[IP贴纸WS] 连接状态异常，退出主循环: %s", exc)
                    break
                except Exception as exc:
                    logger.warning("[IP贴纸WS] 消息处理异常: %s", exc)
                    # 尝试发送错误，失败则退出
                    try:
                        await chat_service._send_error(f"消息处理失败: {exc}")
                    except Exception:
                        break

        except WebSocketDisconnect:
            logger.info("[IP贴纸WS] 连接断开: user_id=%s", user_id)
        except Exception as exc:
            logger.exception("[IP贴纸WS] 连接异常: %s", exc)
        finally:
            await chat_service.on_disconnect()
