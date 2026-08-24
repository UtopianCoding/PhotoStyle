"""
历史记录相关响应模式

所有响应模型使用 camelCase 别名输出，与前端 TypeScript 类型对齐。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.style import TaskResult


class HistoryItem(BaseModel):
    """历史记录条目（列表用，精简字段）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 任务ID
    task_id: str = Field(..., description="任务ID")
    # 技能ID
    skill_id: str = Field(..., description="技能ID")
    # AI 提供商（单模型时返回该模型 ID，多模型时返回首个）
    provider: str = Field(..., description="AI提供商")
    # 实际使用的 Provider 列表（多模型并行时包含多个）
    providers: list[str] = Field(default_factory=list, description="实际使用的 Provider 列表")
    # 输入图片ID
    image_id: str = Field(..., description="图片ID")
    # 原图地址
    original_url: str = Field(..., description="原图URL")
    # 任务状态
    status: str = Field(..., description="任务状态")
    # 结果缩略图列表（精简展示）
    result_thumbnails: list[str] = Field(default_factory=list, description="结果缩略图")
    # 是否有收藏
    has_favorite: bool = Field(default=False, description="是否有收藏")
    # 创建时间
    created_at: datetime = Field(..., description="创建时间")


class HistoryDetail(BaseModel):
    """历史记录详情"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 任务ID
    task_id: str
    # 用户ID
    user_id: str
    # 技能ID
    skill_id: str
    # AI 提供商（单模型时返回该模型 ID，多模型时返回首个）
    provider: str
    # 实际使用的 Provider 列表（多模型并行时包含多个）
    providers: list[str] = Field(default_factory=list, description="实际使用的 Provider 列表")
    # 输入图片ID
    image_id: str
    # 原图地址
    original_url: str
    # 额外提示词
    extra_prompt: str | None = None
    # 任务状态
    status: str
    # 进度
    progress: int = 0
    # 结果列表
    results: list[TaskResult] = Field(default_factory=list)
    # 创建时间
    created_at: datetime


class HistoryListResponse(BaseModel):
    """历史记录列表响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 总条数
    total: int = Field(default=0, description="总条数")
    # 当前页码
    page: int = Field(default=1, description="当前页码")
    # 每页条数
    page_size: int = Field(default=20, description="每页条数")
    # 历史记录列表
    items: list[HistoryItem] = Field(default_factory=list, description="历史记录列表")
