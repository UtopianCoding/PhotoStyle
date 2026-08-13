"""
风格转换结果 ORM 模型

记录每个任务产出的成图、所用提示词与 Provider 原始响应，
并支持收藏标记与积分扣费记录。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StyleResult(Base):
    """风格转换结果表"""

    __tablename__ = "style_results"

    # 自增主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 对外暴露的结果唯一标识
    result_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="结果ID")
    # 所属任务ID
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("style_tasks.task_id"), index=True, nullable=False, comment="任务ID")
    # 所属用户ID
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True, nullable=False, comment="用户ID")
    # 输入图片ID
    image_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="图片ID")
    # 使用的技能ID
    skill_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False, comment="技能ID")
    # AI 提供商
    provider: Mapped[str] = mapped_column(String(32), nullable=False, comment="AI提供商")
    # 结果成图访问地址
    result_url: Mapped[str] = mapped_column(String(512), nullable=False, comment="结果图URL")
    # 结果缩略图地址
    thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="结果缩略图URL")
    # 实际用于生成的完整提示词
    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True, comment="实际提示词")
    # 图片分析结果 JSON
    analysis_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="图片分析JSON")
    # AI 服务商原始响应（用于排查问题）
    provider_response: Mapped[str | None] = mapped_column(Text, nullable=True, comment="服务商原始响应")
    # 是否收藏
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True, comment="是否收藏")
    # 本次结果消耗的积分
    credits_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="消耗积分")
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")

    def __repr__(self) -> str:
        return f"<StyleResult id={self.id} result_id={self.result_id} task_id={self.task_id}>"
