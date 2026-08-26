"""
3D 翻页画册 ORM 模型

包含两个表：
- flipbook_projects: 画册项目元数据
- flipbook_pages: 画册页面内容
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FlipbookProject(Base):
    """画册项目表"""

    __tablename__ = "flipbook_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 对外暴露的画册唯一标识
    project_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, comment="画册项目ID"
    )
    # 所属用户
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id"), index=True, nullable=False, comment="用户ID"
    )
    # 画册标题
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, default="Photo Book", comment="画册标题"
    )
    # 画册眉题
    kicker: Mapped[str | None] = mapped_column(
        String(128), nullable=True, default="Folio", comment="画册眉题"
    )
    # 画册状态：creating / analyzing / ready / error
    status: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False, default="creating", comment="画册状态"
    )
    # 封面图URL（用于列表展示）
    cover_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="封面图URL"
    )
    # AI生成的主题配置（JSON：颜色、纹理、情绪等）
    theme_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="AI生成的主题配置(JSON)"
    )
    # 画册总页数
    page_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="总页数"
    )
    # 来源图片ID列表（JSON数组）
    source_image_ids: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="来源图片ID列表(JSON)"
    )
    # 错误信息
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    def __repr__(self) -> str:
        return f"<FlipbookProject project_id={self.project_id} title={self.title}>"


class FlipbookPage(Base):
    """画册页面表"""

    __tablename__ = "flipbook_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 所属画册
    project_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("flipbook_projects.project_id"), index=True, nullable=False, comment="画册项目ID"
    )
    # 页面ID（前端使用）
    page_id: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="页面ID"
    )
    # 页面排序序号
    page_order: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="页面排序"
    )
    # 图片URL
    image_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="图片URL"
    )
    # 来源图片ID
    source_image_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="来源图片ID"
    )
    # 图片原始宽度
    image_width: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="图片宽度"
    )
    # 图片原始高度
    image_height: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="图片高度"
    )
    # 图片 alt 文本
    alt: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment="图片描述"
    )
    # 页面标题
    caption: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment="页面标题"
    )
    # 页面文本
    text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="页面文本"
    )
    # 图片适配方式：fill / cover / contain
    fit: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="图片适配方式"
    )
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<FlipbookPage page_id={self.page_id} order={self.page_order}>"
