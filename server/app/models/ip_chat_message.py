"""
IP 贴纸聊天消息 ORM 模型

记录会话中每条消息（用户文本 / AI 回复 / 图片生成结果 / 操作指令）。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IPChatMessage(Base):
    """IP 贴纸聊天消息表"""

    __tablename__ = "ip_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, comment="消息ID"
    )
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ip_chat_sessions.session_id"),
        index=True, nullable=False, comment="会话ID"
    )

    # 消息角色：user / assistant / system
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="消息角色"
    )

    # 消息类型（前端渲染判别依据）
    message_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="text|image_single|image_grid|image_generating|"
                "action_confirm|action_select|action_redraw|error",
    )

    # 文本内容
    content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="文本内容"
    )

    # 图片内容 JSON 数组
    images_json: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment='[{"url":"...","thumbnail_url":"...","sticker_id":"...","label":"..."}]',
    )

    # 操作指令 JSON 数组
    actions_json: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment='[{"action":"confirm_base","label":"确认母版"}]',
    )

    # 消息排序序号
    sequence: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="排序序号"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<IPChatMessage message_id={self.message_id} type={self.message_type}>"
