"""
模型交互记录相关路由

提供交互记录列表（分页 + 技能 / 状态筛选）与详情接口，仅本人可见。
"""

import json

from fastapi import APIRouter, Query

from app.api.deps import ConversationRepoDep, CurrentUser
from app.core.exceptions import NotFoundException
from app.schemas.common import ApiResponse
from app.schemas.conversation import (
    ConversationDetail,
    ConversationItem,
    ConversationListResponse,
)

router = APIRouter(prefix="/conversations", tags=["交互记录"])


def _to_item(rec) -> ConversationItem:
    """将 ORM 记录转换为列表项（解析输出图地址 JSON）"""
    try:
        output_urls = json.loads(rec.output_image_urls) if rec.output_image_urls else []
    except (json.JSONDecodeError, TypeError):
        output_urls = []
    return ConversationItem(
        interactionId=rec.interaction_id,
        taskId=rec.task_id,
        skillId=rec.skill_id,
        provider=rec.provider,
        inputImageUrl=rec.input_image_url,
        promptSent=rec.prompt_sent,
        extraPrompt=rec.extra_prompt,
        feedback=rec.feedback,
        location=rec.location,
        outputImageUrls=output_urls,
        outputCount=rec.output_count,
        status=rec.status,
        errorMessage=rec.error_message,
        durationMs=rec.duration_ms,
        createdAt=rec.created_at,
    )


@router.get("", response_model=ApiResponse[ConversationListResponse])
async def list_conversations(
    user: CurrentUser,
    repo: ConversationRepoDep,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    skill_id: str | None = Query(default=None, description="按技能筛选"),
    status: str | None = Query(default=None, description="按状态筛选(success/failed)"),
) -> ApiResponse[ConversationListResponse]:
    """分页获取当前用户的模型交互记录；可按技能 / 状态筛选"""
    offset = (page - 1) * page_size
    records, total = await repo.list_and_count(
        user.user_id, offset=offset, limit=page_size,
        skill_id=skill_id, status=status,
    )
    items = [_to_item(r) for r in records]
    return ApiResponse.success(
        data=ConversationListResponse(
            total=total, page=page, page_size=page_size, items=items
        )
    )


@router.get("/{interaction_id}", response_model=ApiResponse[ConversationDetail])
async def get_conversation_detail(
    interaction_id: str,
    user: CurrentUser,
    repo: ConversationRepoDep,
) -> ApiResponse[ConversationDetail]:
    """获取单条交互记录详情（含服务商原始响应）"""
    rec = await repo.get_by_interaction_id(interaction_id, user.user_id)
    if rec is None:
        raise NotFoundException(f"交互记录 [{interaction_id}] 不存在")
    item = _to_item(rec)
    detail = ConversationDetail(**item.model_dump())
    detail.provider_response = rec.provider_response
    return ApiResponse.success(data=detail)
