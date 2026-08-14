"""
模型服务方相关路由

提供可用 AI 模型服务方列表查询，包含默认 provider 与所有已配置 key 的 provider。
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


class ProvidersListResponse(BaseModel):
    """服务方列表响应（含默认 provider）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 默认使用的 provider ID
    default_provider: str
    # 所有已配置 key 的 provider 列表
    providers: list[ProviderSummary]


@router.get("", response_model=ApiResponse[ProvidersListResponse])
async def list_providers() -> ApiResponse[ProvidersListResponse]:
    """列出所有可用模型服务方及默认 provider"""
    providers: list[ProviderSummary] = []

    # 千问 / DashScope
    if settings.dashscope.api_key.get_secret_value():
        providers.append(
            ProviderSummary(
                id="qianwen",
                name="千问 (DashScope)",
                models=[settings.dashscope.model_image] if settings.dashscope.model_image else [],
            )
        )

    # OpenAI / DALL-E
    if settings.dalle.api_key.get_secret_value():
        providers.append(
            ProviderSummary(
                id="dalle",
                name="OpenAI (DALL-E)",
                models=[settings.dalle.model_image] if settings.dalle.model_image else [],
            )
        )

    # MiniMax
    if settings.minimax.api_key.get_secret_value():
        providers.append(
            ProviderSummary(
                id="minimax",
                name="MiniMax",
                models=[settings.minimax.model_image] if settings.minimax.model_image else [],
            )
        )

    # 豆包
    if (
        settings.doubao.access_key.get_secret_value()
        and settings.doubao.secret_key.get_secret_value()
    ):
        providers.append(
            ProviderSummary(
                id="doubao",
                name="火山引擎 (豆包)",
                models=[],
            )
        )

    data = ProvidersListResponse(
        default_provider=settings.model.default_provider,
        providers=providers,
    )
    return ApiResponse.success(data=data)
