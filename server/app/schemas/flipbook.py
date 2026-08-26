"""
3D 翻页画册 Schema
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class FlipbookPageRead(BaseModel):
    """画册页面读取响应"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    page_id: str
    page_order: int
    image_url: str | None = None
    source_image_id: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    alt: str | None = None
    caption: str | None = None
    text: str | None = None
    fit: str | None = None


class FlipbookProjectRead(BaseModel):
    """画册项目读取响应"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    project_id: str
    title: str
    kicker: str | None = None
    status: str
    cover_url: str | None = None
    theme_json: str | None = None  # AI生成的主题配置
    page_count: int
    error_message: str | None = None  # 错误信息
    pages: list[FlipbookPageRead] = []
    created_at: datetime
    updated_at: datetime


class FlipbookProjectBrief(BaseModel):
    """画册项目简要信息（用于列表）"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    project_id: str
    title: str
    kicker: str | None = None
    status: str
    cover_url: str | None = None
    page_count: int
    created_at: datetime


class FlipbookListResponse(BaseModel):
    """画册列表响应"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    total: int
    page: int
    page_size: int
    items: list[FlipbookProjectBrief]


class CreateFlipbookRequest(BaseModel):
    """创建画册请求"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str = "Photo Book"
    kicker: str | None = "Folio"
    result_ids: list[str]  # 转换结果ID列表（从 style_results 中选取）
