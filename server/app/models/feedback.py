"""
反馈 ORM 模型

记录用户反馈与建议，支持管理员回复。
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Feedback(Base):
    """反馈模型"""

    __tablename__ = "feedbacks"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 反馈唯一标识
    feedback_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # 用户ID（关联 users.user_id）
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # 反馈内容
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 附件图片URL列表（JSON字符串）
    images: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 状态：pending/replied/resolved/closed
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)

    # 管理员回复内容
    admin_reply: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 回复人ID（管理员user_id）
    replied_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 回复时间
    replied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} feedback_id={self.feedback_id} user_id={self.user_id} status={self.status}>"
