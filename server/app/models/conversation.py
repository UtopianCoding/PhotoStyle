"""
模型交互记录 ORM 模型

记录每次与 AI 图像生成模型的交互过程，便于审计与回溯：
- 输入：原图地址、最终发给模型的完整提示词（含所有分析 + 额外要求 + 重生成意见）、
       技能、提供商、用户额外要求、重新生成意见、冰箱贴地点
- 输出：生成结果图地址（JSON 列表）、结果数量、服务商原始响应
- 元数据：关联任务、耗时、成功/失败、错误信息、创建时间
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModelInteraction(Base):
    """模型交互记录表"""

    __tablename__ = "model_interactions"

    # 自增主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 对外暴露的交互记录唯一标识
    interaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="交互记录ID")
    # 关联的风格转换任务ID
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("style_tasks.task_id"), index=True, nullable=False, comment="任务ID")
    # 所属用户ID
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True, nullable=False, comment="用户ID")
    # 使用的技能ID（如 photo-revival / ink-minimalist）
    skill_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False, comment="技能ID")
    # AI 提供商标识：qianwen / doubao / dalle
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="qianwen", comment="AI提供商")

    # -------------------- 输入 --------------------
    # 输入原图地址
    input_image_url: Mapped[str] = mapped_column(Text, nullable=False, comment="输入原图地址")
    # 最终发给模型的完整提示词（含分析、额外要求、重新生成意见）
    prompt_sent: Mapped[str] = mapped_column(Text, nullable=False, comment="实际发送给模型的提示词")
    # 用户额外提示词（未叠加进 prompt 之前的原始要求）
    extra_prompt: Mapped[str | None] = mapped_column(Text, nullable=True, comment="用户额外提示词")
    # 重新生成时用户填写的修改意见
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True, comment="重新生成修改意见")
    # 冰箱贴等技能使用的拍摄地点
    location: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="拍摄地点")

    # -------------------- 输出 --------------------
    # 输出结果图地址列表（JSON 数组字符串）
    output_image_urls: Mapped[str] = mapped_column(Text, nullable=False, default="[]", comment="输出结果图地址(JSON列表)")
    # 输出结果数量
    output_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="输出结果数量")
    # AI 服务商原始响应（用于排查问题）
    provider_response: Mapped[str | None] = mapped_column(Text, nullable=True, comment="服务商原始响应")

    # -------------------- 状态 --------------------
    # 交互状态：success / failed
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="success", comment="交互状态")
    # 错误信息（失败时）
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    # 本次交互耗时（毫秒）
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="耗时(毫秒)")

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")

    def __repr__(self) -> str:
        return f"<ModelInteraction id={self.id} interaction_id={self.interaction_id} status={self.status}>"
