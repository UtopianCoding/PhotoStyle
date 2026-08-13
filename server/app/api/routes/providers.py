"""
模型服务方相关路由

提供可用 AI 模型服务方列表查询。
"""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.config import settings
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/providers", tags=["模型服务方"])


class ProviderSummary(BaseModel):
    """服务方摘要"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str = Field(..., description="服务方ID")
    name: str
    models: list[str] = Field(default_factory=list)


@router.get("", response_model=ApiResponse[list[ProviderSummary]])
async def list_providers() -> ApiResponse[list[ProviderSummary]]:
    """列出所有可用模型服务方"""
    providers: list[ProviderSummary] = []

    # 千问 / DashScope
    if settings.dashscope.api_key:
        providers.append(
            ProviderSummary(
                id="dashscope",
                name="千问 (DashScope)",
                models=[settings.dashscope.image_model] if settings.dashscope.image_model else [],
            )
        )

    return ApiResponse.success(data=providers)
