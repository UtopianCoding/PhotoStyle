"""
IP 贴纸结果 ORM 模型

记录每张贴纸的生成结果（测试批次 / 完整批次 / 单张重绘）。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IPStickerResult(Base):
    """IP 贴纸结果表"""

    __tablename__ = "ip_sticker_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sticker_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, comment="贴纸ID"
    )
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ip_chat_sessions.session_id"),
        index=True, nullable=False, comment="会话ID"
    )
    template_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ip_master_templates.template_id"),
        index=True, nullable=False, comment="母版ID"
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id"),
        index=True, nullable=False, comment="用户ID"
    )

    # 贴纸序号（1-20）
    sticker_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="贴纸序号"
    )

    # 贴纸描述（表情/姿态）
    label: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="表情/姿态描述"
    )

    # 生成此贴纸使用的完整提示词
    generation_prompt: Mapped[str] = mapped_column(
        Text, nullable=False, comment="生成提示词"
    )

    # 贴纸图片 URL
    result_url: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="贴纸图片URL"
    )
    # 缩略图 URL
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="缩略图URL"
    )

    # 状态：pending / generating / success / failed
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", comment="状态"
    )

    # 生成批次：test_batch(4张) / full_batch(20张) / redraw(单张重绘)
    batch_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="批次类型"
    )

    # 是否被用户收藏
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否收藏"
    )

    # 错误信息
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )

    # 重绘次数
    redraw_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="重绘次数"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<IPStickerResult sticker_id={self.sticker_id} label={self.label} status={self.status}>"
