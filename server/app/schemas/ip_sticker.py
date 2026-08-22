"""
IP 贴纸相关 Pydantic 模式
"""

from datetime import datetime

from pydantic import BaseModel, Field


class SessionItem(BaseModel):
    """会话列表项"""
    session_id: str
    status: str
    current_step: int
    source_image_id: str | None = None
    created_at: datetime
    updated_at: datetime


class SessionDetail(BaseModel):
    """会话详情（含消息历史）"""
    session_id: str
    user_id: str
    status: str
    current_step: int
    source_image_id: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list["MessageItem"] = Field(default_factory=list)
    master_template: "MasterTemplateItem | None" = None
    stickers: list["StickerItem"] = Field(default_factory=list)


class MessageItem(BaseModel):
    """聊天消息"""
    message_id: str
    role: str
    message_type: str
    content: str | None = None
    images: list[dict] | None = None
    actions: list[dict] | None = None
    sequence: int
    created_at: datetime


class MasterTemplateItem(BaseModel):
    """IP 母版"""
    template_id: str
    master_image_url: str
    master_thumbnail_url: str | None = None
    character_description: str | None = None
    version: int
    is_locked: bool
    created_at: datetime


class StickerItem(BaseModel):
    """贴纸结果"""
    sticker_id: str
    sticker_index: int
    label: str
    result_url: str
    thumbnail_url: str | None = None
    status: str
    batch_type: str
    is_favorite: bool
    redraw_count: int
    created_at: datetime


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    image_id: str | None = Field(None, description="源图片ID（可选，也可后续通过 WS 设置）")


class SendMessageRequest(BaseModel):
    """发送消息请求（REST 降级方案）"""
    type: str = Field(description="消息类型")
    payload: dict = Field(default_factory=dict, description="消息内容")


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: list[SessionItem]
