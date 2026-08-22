"""
AI 模块通用模式

定义 Provider 层统一的请求/响应结构与图片分析结果模式。
"""

from typing import Any

from pydantic import BaseModel, Field


class ImageOptions(BaseModel):
    """图像生成选项"""

    # 输出比例，如 "3:4"
    ratio: str = Field(default="3:4", description="输出比例")
    # 输出尺寸字符串（部分提供商直接使用，如 "768*1024"）
    size: str | None = Field(default=None, description="输出尺寸")
    # 生成数量
    num_results: int = Field(default=1, ge=1, le=4, description="生成数量")
    # 额外参数（各提供商特有参数，如 seed）
    extra: dict[str, Any] = Field(default_factory=dict, description="额外参数")


class ImageProviderRequest(BaseModel):
    """Provider 统一请求"""

    # 提示词
    prompt: str = Field(..., description="提示词")
    # 输入图片地址（图生图场景；文生图可为空）
    image_url: str | None = Field(default=None, description="输入图片URL")
    # 参考图片列表（风格参考图，会一起发给模型）
    reference_images: list[str] = Field(default_factory=list, description="参考图片URL列表")
    # 模型名（缺省由 Provider 自行决定）
    model: str | None = Field(default=None, description="模型名")
    # 生成选项
    options: ImageOptions = Field(default_factory=ImageOptions, description="生成选项")


class ImageResult(BaseModel):
    """单张生成结果"""

    # 结果图地址
    url: str = Field(..., description="结果图URL")
    # 缩略图地址
    thumbnail_url: str | None = Field(default=None, description="缩略图URL")
    # 宽度
    width: int | None = Field(default=None, description="宽度")
    # 高度
    height: int | None = Field(default=None, description="高度")
    # 原始元数据
    metadata: dict[str, Any] = Field(default_factory=dict, description="原始元数据")


class ImageProviderResponse(BaseModel):
    """Provider 统一响应"""

    # 任务状态：success / pending / failed
    status: str = Field(..., description="任务状态")
    # 生成结果列表
    results: list[ImageResult] = Field(default_factory=list, description="结果列表")
    # 服务商异步任务ID（若为异步任务且尚未完成）
    provider_task_id: str | None = Field(default=None, description="服务商任务ID")
    # 服务商原始响应（用于排查问题）
    raw_response: dict[str, Any] | None = Field(default=None, description="原始响应")
    # 错误信息
    error: str | None = Field(default=None, description="错误信息")


class ImageAnalysis(BaseModel):
    """图片分析结果"""

    # 主体
    subject: str | None = Field(default=None, description="主体")
    # 场景
    scene: str | None = Field(default=None, description="场景")
    # 情绪
    mood: str | None = Field(default=None, description="情绪")
    # 构图
    composition: str | None = Field(default=None, description="构图")
    # 主色调列表
    colors: list[str] = Field(default_factory=list, description="主色调")
    # 关键物件列表
    key_objects: list[str] = Field(default_factory=list, description="关键物件")
    # 原始响应
    raw: dict[str, Any] | None = Field(default=None, description="原始响应")
