"""
模型交互记录相关响应模式

所有响应模型使用 camelCase 别名输出，与前端 TypeScript 类型对齐。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ConversationItem(BaseModel):
    """交互记录条目（列表用，精简字段）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 交互记录ID
    interaction_id: str = Field(..., description="交互记录ID")
    # 关联任务ID
    task_id: str = Field(..., description="任务ID")
    # 技能ID
    skill_id: str = Field(..., description="技能ID")
    # AI 提供商
    provider: str = Field(..., description="AI提供商")
    # 输入原图地址
    input_image_url: str = Field(..., description="输入原图地址")
    # 最终发送给模型的提示词
    prompt_sent: str = Field(..., description="发送给模型的提示词")
    # 用户额外提示词
    extra_prompt: str | None = Field(default=None, description="用户额外提示词")
    # 重新生成修改意见
    feedback: str | None = Field(default=None, description="重新生成意见")
    # 拍摄地点
    location: str | None = Field(default=None, description="拍摄地点")
    # 输出结果图地址列表
    output_image_urls: list[str] = Field(default_factory=list, description="输出结果图地址")
    # 输出结果数量
    output_count: int = Field(default=0, description="输出结果数量")
    # 交互状态
    status: str = Field(..., description="交互状态")
    # 错误信息
    error_message: str | None = Field(default=None, description="错误信息")
    # 耗时（毫秒）
    duration_ms: int | None = Field(default=None, description="耗时(毫秒)")
    # 创建时间
    created_at: datetime = Field(..., description="创建时间")


class ConversationListResponse(BaseModel):
    """交互记录列表响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 总条数
    total: int = Field(default=0, description="总条数")
    # 当前页码（从 1 开始）
    page: int = Field(default=1, description="当前页码")
    # 每页条数
    page_size: int = Field(default=20, description="每页条数")
    # 交互记录列表
    items: list[ConversationItem] = Field(default_factory=list, description="交互记录列表")


class ConversationDetail(ConversationItem):
    """交互记录详情（继承列表项，额外暴露服务商原始响应）"""

    # AI 服务商原始响应（JSON 字符串）
    provider_response: str | None = Field(default=None, description="服务商原始响应")
