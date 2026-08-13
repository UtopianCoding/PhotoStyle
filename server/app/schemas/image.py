"""
图片相关请求/响应模式

所有响应模型使用 camelCase 别名输出，与前端 TypeScript 类型对齐。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ImageUploadResponse(BaseModel):
    """图片上传响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 对外图片ID
    image_id: str = Field(..., description="图片ID")
    # 原图访问地址
    original_url: str = Field(..., description="原图URL")
    # 缩略图访问地址
    thumbnail_url: str | None = Field(default=None, description="缩略图URL")
    # MIME 类型
    mime_type: str = Field(..., description="MIME类型")
    # 宽度
    width: int | None = Field(default=None, description="宽度")
    # 高度
    height: int | None = Field(default=None, description="高度")
    # 文件大小（字节）
    size: int | None = Field(default=None, description="文件大小")
    # 是否已压缩
    compressed: bool = Field(default=False, description="是否已压缩")
    # 压缩比
    compressed_ratio: float | None = Field(default=None, description="压缩比")
    # 创建时间
    created_at: datetime | None = Field(default=None, description="创建时间")


class ImageInfo(BaseModel):
    """图片信息"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 对外图片ID
    image_id: str
    # 原图地址
    original_url: str
    # 缩略图地址
    thumbnail_url: str | None = None
    # MIME 类型
    mime_type: str
    # 宽度
    width: int | None = None
    # 高度
    height: int | None = None
    # 文件大小
    size: int | None = None
    # 是否压缩
    compressed: bool = False
    # 压缩比
    compressed_ratio: float | None = None
    # 创建时间
    created_at: datetime | None = None


class ImageDeleteResponse(BaseModel):
    """图片删除响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 是否删除成功
    success: bool = Field(..., description="是否删除成功")
    # 被删除的图片ID
    image_id: str = Field(..., description="图片ID")
