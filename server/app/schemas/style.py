"""
风格转换相关请求/响应模式

所有响应模型使用 camelCase 别名输出，与前端 TypeScript 类型对齐。
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class StyleOptions(BaseModel):
    """风格选项"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 输出比例，如 "3:4"、"1:1"、"4:3"、"16:9"
    ratio: str = Field(default="3:4", description="输出比例")
    # 主体比例（占比百分比，仅用于 photo-revival 等技能）
    subject_ratio: str = Field(default="10-16%", description="主体占比")
    # 生成数量
    num_results: int = Field(default=1, ge=1, le=4, description="生成数量")


class ConvertRequest(BaseModel):
    """风格转换请求"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 输入图片ID
    image_id: str = Field(..., description="图片ID")
    # 技能ID（如 photo-revival），默认使用老照片复兴
    skill_id: str = Field(default="photo-revival", description="技能ID")
    # AI 提供商：qianwen / doubao / dalle
    provider: str = Field(default="qianwen", description="AI提供商")
    # 额外提示词（用户补充要求）
    extra_prompt: str | None = Field(default=None, description="额外提示词")
    # 风格选项
    options: StyleOptions = Field(default_factory=StyleOptions, description="风格选项")
    # 从分析步骤获得的最终英文提示词（如果提供，则跳过后台分析直接使用）
    final_prompt: str | None = Field(default=None, description="分析步骤生成的最终提示词")
    # 用户选择的诗意小字（可选）
    poetic_text: str | None = Field(default=None, description="用户选择的诗意小字")
    # 拍摄地点（可选）：冰箱贴等需要英文城市名排版的技能使用，如「昆明/中国」
    location: str | None = Field(default=None, description="拍摄地点")
    # 重新生成时用户填写的修改意见（可选）：将在原提示词基础上叠加后交给模型
    feedback: str | None = Field(default=None, description="重新生成的修改意见")


class AnalyzeRequest(BaseModel):
    """图片分析请求"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 输入图片ID
    image_id: str = Field(..., description="图片ID")
    # 技能ID（可选）：用户手动指定时使用，留空则由后端按图片内容自动推荐
    skill_id: str = Field(default="", description="技能ID")
    # 额外提示词（可选）
    extra_prompt: str | None = Field(default=None, description="额外提示词")
    # 拍摄地点（可选）：冰箱贴等需要英文城市名排版的技能使用，如「昆明/中国」
    location: str | None = Field(default=None, description="拍摄地点")


class AnalyzeResponse(BaseModel):
    """图片分析响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 推荐使用的技能 ID（根据图片内容自动判断：风景/城市场景推荐 city-editorial，其余 photo-revival）
    recommended_skill_id: str = Field(
        default="photo-revival", description="推荐使用的技能ID"
    )
    # 照片主体识别（中文详细描述）
    subject_analysis: str = Field(default="", description="主体分析")
    # 需要保留的核心元素
    core_elements: list[str] = Field(default_factory=list, description="核心元素")
    # 插画规则
    rules: dict[str, Any] = Field(default_factory=dict, description="插画规则")
    # 特殊元素处理建议
    special_notes: str = Field(default="", description="特殊元素处理建议")
    # 最终英文提示词（直接可用于 AI 图像生成）
    final_prompt: str = Field(default="", description="最终英文提示词")
    # 诗意小字备选列表
    poetic_options: list[str] = Field(default_factory=list, description="诗意小字备选")
    # 使用建议
    suggestions: list[str] = Field(default_factory=list, description="使用建议")


class ConvertResponse(BaseModel):
    """风格转换响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 任务ID
    task_id: str = Field(..., description="任务ID")
    # 任务状态
    status: str = Field(default="pending", description="任务状态")
    # 技能ID
    skill_id: str = Field(..., description="技能ID")
    # AI 提供商
    provider: str = Field(..., description="AI提供商")
    # 预计耗时（秒）
    estimated_time: int = Field(default=30, description="预计耗时(秒)")


class TaskResult(BaseModel):
    """任务结果"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 结果ID
    result_id: str
    # 结果图地址
    result_url: str
    # 缩略图地址
    thumbnail_url: str | None = None
    # 是否收藏
    favorite: bool = False
    # 创建时间
    created_at: datetime | None = None


class TaskStatusResponse(BaseModel):
    """任务状态响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 任务ID
    task_id: str = Field(..., description="任务ID")
    # 输入图片ID
    image_id: str = Field(..., description="图片ID")
    # 原图地址（前端结果页可独立展示，无需依赖上传态 store）
    original_url: str = Field(default="", description="原图URL")
    # 任务状态：pending / running / success / failed / canceled
    status: str = Field(..., description="任务状态")
    # 执行阶段
    stage: str | None = Field(default=None, description="执行阶段")
    # 进度百分比
    progress: int = Field(default=0, ge=0, le=100, description="进度")
    # 提示信息
    message: str | None = Field(default=None, description="提示信息")
    # 任务结果列表（成功时返回）
    results: list[TaskResult] = Field(default_factory=list, description="任务结果")
    # 错误信息
    error: str | None = Field(default=None, description="错误信息")
    # 本次生成实际使用的完整提示词（成功时返回首个结果）：前端用于「重新生成」时回传原提示词
    final_prompt: str | None = Field(default=None, description="实际使用的完整提示词")
