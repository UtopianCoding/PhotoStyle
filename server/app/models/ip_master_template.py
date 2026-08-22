"""
IP 母版 ORM 模型

记录用户确认的 IP 角色定型图 + 特征描述。
母版锁定后，后续所有贴纸生成共用 character_prompt 保证一致性。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IPMasterTemplate(Base):
    """IP 母版表"""

    __tablename__ = "ip_master_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, comment="母版ID"
    )
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ip_chat_sessions.session_id"),
        index=True, nullable=False, comment="会话ID"
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id"),
        index=True, nullable=False, comment="用户ID"
    )

    # 母版图 URL（最终确认版）
    master_image_url: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="母版图URL"
    )
    # 母版缩略图 URL
    master_thumbnail_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="母版缩略图URL"
    )

    # AI 生成的角色特征描述（英文，用于后续生成时保持一致性）
    character_prompt: Mapped[str] = mapped_column(
        Text, nullable=False, comment="角色特征英文提示词"
    )

    # 角色特征中文描述（展示给用户）
    character_description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="角色特征中文描述"
    )

    # 生成母版时使用的完整提示词
    generation_prompt: Mapped[str] = mapped_column(
        Text, nullable=False, comment="完整生成提示词"
    )

    # 版本号（用户确认修改后递增）
    version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="版本号"
    )

    # 是否已锁定
    is_locked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否已锁定"
    )

    # 历史版本 URL（JSON 数组）
    version_history_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="历史版本URL数组"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="锁定时间"
    )

    def __repr__(self) -> str:
        return f"<IPMasterTemplate template_id={self.template_id} v{self.version} locked={self.is_locked}>"
