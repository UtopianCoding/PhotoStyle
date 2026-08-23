"""
模型服务方相关路由

提供可用 AI 模型服务方列表查询，包含默认 provider 与所有已配置 key 的 provider。
配置从数据库内存缓存读取，运行时修改立即生效。
"""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.common import ApiResponse
from app.services.model_config_store import model_config_store

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
    store = model_config_store
    providers: list[ProviderSummary] = []

    # 千问 / DashScope
    qw = store.get_config("qianwen") or {}
    if qw.get("api_key"):
        model_img = qw.get("model_image", "")
        providers.append(
            ProviderSummary(
                id="qianwen",
                name="千问 (DashScope)",
                models=[model_img] if model_img else [],
            )
        )

    # OpenAI / DALL-E
    dl = store.get_config("dalle") or {}
    if dl.get("api_key"):
        model_img = dl.get("model_image", "")
        providers.append(
            ProviderSummary(
                id="dalle",
                name="OpenAI (DALL-E)",
                models=[model_img] if model_img else [],
            )
        )

    # MiniMax
    mm = store.get_config("minimax") or {}
    if mm.get("api_key"):
        model_img = mm.get("model_image", "")
        providers.append(
            ProviderSummary(
                id="minimax",
                name="MiniMax",
                models=[model_img] if model_img else [],
            )
        )

    # 火山引擎（Seedream）
    vc = store.get_config("volcengine") or {}
    if vc.get("api_key"):
        model_img = vc.get("model_image", "")
        providers.append(
            ProviderSummary(
                id="volcengine",
                name="火山引擎 (Seedream)",
                models=[model_img] if model_img else [],
            )
        )

    # 豆包
    db_ = store.get_config("doubao") or {}
    if db_.get("access_key") and db_.get("secret_key"):
        providers.append(
            ProviderSummary(
                id="doubao",
                name="火山引擎 (豆包)",
                models=[],
            )
        )

    data = ProvidersListResponse(
        default_provider=store.get_default_provider(),
        providers=providers,
    )
    return ApiResponse.success(data=data)
