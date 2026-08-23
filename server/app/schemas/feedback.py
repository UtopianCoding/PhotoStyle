"""
反馈相关请求/响应模式

所有响应模型使用 camelCase 别名输出，与前端 TypeScript 类型对齐。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class FeedbackCreate(BaseModel):
    """创建反馈请求"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 反馈内容（必填）
    content: str = Field(..., min_length=15, max_length=2000, description="反馈内容（至少15个字）")
    # 附件图片URL列表（可选，最多5张）
    images: Optional[List[str]] = Field(default=None, max_length=5, description="反馈附图URL列表")


class FeedbackInfo(BaseModel):
    """反馈信息（用户视角）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 反馈ID
    feedback_id: str = Field(..., description="反馈ID")
    # 用户ID
    user_id: str = Field(..., description="用户ID")
    # 反馈内容
    content: str = Field(..., description="反馈内容")
    # 附件图片
    images: Optional[List[str]] = Field(default=None, description="反馈附图URL列表")
    # 状态：pending/replied/resolved/closed
    status: str = Field(..., description="反馈状态")
    # 管理员回复
    admin_reply: Optional[str] = Field(default=None, description="管理员回复")
    # 回复人ID
    replied_by: Optional[str] = Field(default=None, description="回复人ID")
    # 回复时间
    replied_at: Optional[datetime] = Field(default=None, description="回复时间")
    # 创建时间
    created_at: datetime = Field(..., description="创建时间")
    # 更新时间
    updated_at: datetime = Field(..., description="更新时间")


class FeedbackReply(BaseModel):
    """管理员回复请求"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 回复内容（必填）
    reply: str = Field(..., min_length=1, max_length=5000, description="回复内容")


class FeedbackStatusUpdate(BaseModel):
    """更新反馈状态请求"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 新状态（必填）
    status: str = Field(..., description="反馈状态：pending/replied/resolved/closed")


class AdminFeedbackItem(BaseModel):
    """反馈信息（管理员视角，包含用户信息）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 反馈ID
    feedback_id: str = Field(..., description="反馈ID")
    # 用户ID
    user_id: str = Field(..., description="用户ID")
    # 用户邮箱
    user_email: str = Field(..., description="用户邮箱")
    # 用户昵称
    user_nickname: Optional[str] = Field(default=None, description="用户昵称")
    # 用户头像
    user_avatar_url: Optional[str] = Field(default=None, description="用户头像URL")
    # 反馈内容
    content: str = Field(..., description="反馈内容")
    # 附件图片
    images: Optional[List[str]] = Field(default=None, description="反馈附图URL列表")
    # 状态：pending/replied/resolved/closed
    status: str = Field(..., description="反馈状态")
    # 管理员回复
    admin_reply: Optional[str] = Field(default=None, description="管理员回复")
    # 回复人ID
    replied_by: Optional[str] = Field(default=None, description="回复人ID")
    # 回复时间
    replied_at: Optional[datetime] = Field(default=None, description="回复时间")
    # 创建时间
    created_at: datetime = Field(..., description="创建时间")
    # 更新时间
    updated_at: datetime = Field(..., description="更新时间")
