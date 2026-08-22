"""
IP 贴纸聊天会话 ORM 模型

记录一次完整的 IP 贴纸制作流程：上传照片 → 确认母版 → 测试贴纸 → 完整贴纸集。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IPChatSession(Base):
    """IP 贴纸聊天会话表"""

    __tablename__ = "ip_chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, comment="会话ID"
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id"), index=True, nullable=False, comment="用户ID"
    )

    # 关联的源图片（用户上传的照片）
    source_image_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("images.image_id"), nullable=True, comment="源图片ID"
    )

    # 会话状态机
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="awaiting_photo",
        comment="状态: awaiting_photo|generating_base|reviewing_base|"
                "generating_test|reviewing_test|generating_batch|"
                "previewing|selecting|redrawing|completed|abandoned",
    )

    # 当前步骤号（0-8）
    current_step: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="当前步骤号"
    )

    # 扩展元数据 JSON
    metadata_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="扩展元数据JSON"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(),
        nullable=False, comment="更新时间"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="完成时间"
    )

    def __repr__(self) -> str:
        return f"<IPChatSession session_id={self.session_id} status={self.status}>"
