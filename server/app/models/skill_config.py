"""
技能配置 ORM 模型

数据库管理的技能配置，支持动态新增、编辑、启用/禁用。
与文件系统技能（SKILL.md）共存，数据库技能优先级更高。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SkillConfig(Base):
    """技能配置表"""

    __tablename__ = "skill_configs"

    # 自增主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 技能唯一标识（如 photo-revival）
    skill_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, comment="技能ID"
    )
    # 技能名称
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="技能名称"
    )
    # 技能描述
    description: Mapped[str] = mapped_column(
        Text, nullable=True, comment="技能描述"
    )
    # 提示词模板
    prompt_template: Mapped[str] = mapped_column(
        Text, nullable=False, comment="提示词模板"
    )
    # 推荐 AI 提供商
    provider: Mapped[str] = mapped_column(
        String(32), default="qianwen", nullable=False, comment="AI提供商"
    )
    # 默认输出比例
    ratio: Mapped[str] = mapped_column(
        String(16), default="3:4", nullable=False, comment="输出比例"
    )
    # 主体占比
    subject_ratio: Mapped[str] = mapped_column(
        String(16), default="10-16%", nullable=False, comment="主体占比"
    )
    # 技能分类
    category: Mapped[str] = mapped_column(
        String(64), default="默认", nullable=False, comment="技能分类"
    )
    # 预览图 URL（单张，兼容旧版）
    preview_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="预览图URL"
    )
    # 多张预览图 URL（JSON 数组，用于首页 2x2 网格展示）
    preview_urls: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="多张预览图URL(JSON数组)"
    )
    # 是否启用（前端展示）
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否启用"
    )
    # 是否需要图片分析
    need_analysis: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否需要图片分析"
    )
    # 排序权重（数字越小越靠前）
    sort_order: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False, comment="排序权重"
    )
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<SkillConfig id={self.id} skill_id={self.skill_id} name={self.name}>"
