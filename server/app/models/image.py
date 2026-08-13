"""
图片 ORM 模型

记录用户上传的原图信息，包括尺寸、压缩信息等，供风格转换任务引用。
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Image(Base):
    """图片表"""

    __tablename__ = "images"

    # 自增主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 对外暴露的图片唯一标识
    image_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="图片ID")
    # 所属用户ID（关联 users.user_id）
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True, nullable=False, comment="用户ID")
    # 原图访问地址
    original_url: Mapped[str] = mapped_column(String(512), nullable=False, comment="原图URL")
    # 缩略图访问地址
    thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="缩略图URL")
    # MIME 类型，如 image/jpeg
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="MIME类型")
    # 图片宽度（像素）
    width: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="宽度")
    # 图片高度（像素）
    height: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="高度")
    # 文件大小（字节）
    size: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="文件大小")
    # 是否已压缩
    compressed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否已压缩")
    # 压缩比（压缩后大小 / 原始大小）
    compressed_ratio: Mapped[float | None] = mapped_column(Float, nullable=True, comment="压缩比")
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")

    def __repr__(self) -> str:
        return f"<Image id={self.id} image_id={self.image_id} user_id={self.user_id}>"
