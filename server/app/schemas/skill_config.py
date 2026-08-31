"""
技能配置相关请求/响应模式

所有响应模型使用 camelCase 别名输出，与前端 TypeScript 类型对齐。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class SkillConfigCreate(BaseModel):
    """创建技能配置请求"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 技能ID（唯一标识）
    skill_id: str = Field(..., min_length=1, max_length=64, description="技能ID")
    # 技能名称
    name: str = Field(..., min_length=1, max_length=128, description="技能名称")
    # 技能描述
    description: str | None = Field(default=None, description="技能描述")
    # 提示词模板
    prompt_template: str = Field(..., min_length=1, description="提示词模板")
    # 推荐 AI 提供商
    provider: str = Field(default="qianwen", max_length=32, description="AI提供商")
    # 默认输出比例
    ratio: str = Field(default="3:4", max_length=16, description="输出比例")
    # 主体占比
    subject_ratio: str = Field(default="10-16%", max_length=16, description="主体占比")
    # 技能分类
    category: str = Field(default="默认", max_length=64, description="技能分类")
    # 预览图 URL
    preview_url: str | None = Field(default=None, max_length=512, description="预览图URL")
    # 多张预览图URL列表
    preview_urls: list[str] | None = Field(default=None, description="多张预览图URL")
    # 是否启用
    is_active: bool = Field(default=True, description="是否启用")
    # 是否需要图片分析
    need_analysis: bool = Field(default=True, description="是否需要图片分析")
    # 输入变量（技能声明需要用户填写的变量，如地点/签名；替换提示词模板 {{KEY}} 占位符）
    input_variables: list[dict] | None = Field(default=None, description="输入变量列表")
    # 排序权重
    sort_order: int = Field(default=100, description="排序权重")


class SkillConfigUpdate(BaseModel):
    """更新技能配置请求"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )

    # 技能名称
    name: str | None = Field(default=None, min_length=1, max_length=128, description="技能名称")
    # 技能描述
    description: str | None = Field(default=None, description="技能描述")
    # 提示词模板
    prompt_template: str | None = Field(default=None, min_length=1, description="提示词模板")
    # 推荐 AI 提供商
    provider: str | None = Field(default=None, max_length=32, description="AI提供商")
    # 默认输出比例
    ratio: str | None = Field(default=None, max_length=16, description="输出比例")
    # 主体占比
    subject_ratio: str | None = Field(default=None, max_length=16, description="主体占比")
    # 技能分类
    category: str | None = Field(default=None, max_length=64, description="技能分类")
    # 预览图 URL
    preview_url: str | None = Field(default=None, max_length=512, description="预览图URL")
    # 多张预览图URL列表
    preview_urls: list[str] | None = Field(default=None, description="多张预览图URL")
    # 是否启用
    is_active: bool | None = Field(default=None, description="是否启用")
    # 是否需要图片分析
    need_analysis: bool | None = Field(default=None, description="是否需要图片分析")
    # 输入变量（技能声明需要用户填写的变量，如地点/签名；替换提示词模板 {{KEY}} 占位符）
    input_variables: list[dict] | None = Field(default=None, description="输入变量列表")
    # 排序权重
    sort_order: int | None = Field(default=None, description="排序权重")


class SkillConfigResponse(BaseModel):
    """技能配置响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 数据库ID
    id: int
    # 技能ID
    skill_id: str
    # 技能名称
    name: str
    # 技能描述
    description: str | None = None
    # 提示词模板
    prompt_template: str
    # 推荐 AI 提供商
    provider: str = "qianwen"
    # 默认输出比例
    ratio: str = "3:4"
    # 主体占比
    subject_ratio: str = "10-16%"
    # 技能分类
    category: str = "默认"
    # 预览图 URL
    preview_url: str | None = None
    # 多张预览图URL列表
    preview_urls: list[str] = []
    # 是否启用
    is_active: bool = True
    # 是否需要图片分析
    need_analysis: bool = True
    # 输入变量（技能声明需要用户填写的变量，如地点/签名；替换提示词模板 {{KEY}} 占位符）
    input_variables: list[dict] = Field(default_factory=list, description="输入变量列表")
    # 排序权重
    sort_order: int = 100
    # 创建时间
    created_at: datetime
    # 更新时间
    updated_at: datetime


class SkillConfigListResponse(BaseModel):
    """技能配置列表响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 技能列表
    items: list[SkillConfigResponse]
    # 总数
    total: int
