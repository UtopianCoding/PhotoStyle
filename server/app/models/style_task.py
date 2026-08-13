"""
风格转换任务 ORM 模型

记录一次风格转换请求的执行状态、阶段、进度及错误信息。
任务状态机：pending -> running -> success / failed / canceled
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StyleTask(Base):
    """风格转换任务表"""

    __tablename__ = "style_tasks"

    # 自增主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 对外暴露的任务唯一标识
    task_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="任务ID")
    # 所属用户ID
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True, nullable=False, comment="用户ID")
    # 输入图片ID
    image_id: Mapped[str] = mapped_column(String(64), ForeignKey("images.image_id"), nullable=False, comment="图片ID")
    # 使用的技能ID（如 photo-revival）
    skill_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False, comment="技能ID")
    # AI 提供商标识：qianwen / doubao / dalle
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="qianwen", comment="AI提供商")
    # 额外提示词（用户补充要求）
    extra_prompt: Mapped[str | None] = mapped_column(Text, nullable=True, comment="额外提示词")
    # 风格选项 JSON（如 ratio、num_results 等）
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="风格选项JSON")
    # 任务状态：pending / running / success / failed / canceled
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="pending", comment="任务状态")
    # 执行阶段：queued / analyzing / generating / uploading / done
    stage: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="执行阶段")
    # 进度百分比（0-100）
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="进度")
    # 错误码（业务自定义）
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="错误码")
    # 错误信息
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    # AI 服务商返回的任务ID（用于轮询）
    provider_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="服务商任务ID")
    # 任务开始执行时间
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    # 任务完成时间
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="完成时间")
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")

    def __repr__(self) -> str:
        return f"<StyleTask id={self.id} task_id={self.task_id} status={self.status}>"
