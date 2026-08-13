"""
历史记录相关路由

提供历史列表、详情、收藏、删除与批量删除接口。

注意：固定路径（/favorites、/batch）必须定义在动态路径 /{result_id} 之前，
否则会被 /{result_id} 误匹配。
"""

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.api.deps import CurrentUser, HistoryServiceDep
from app.schemas.common import ApiResponse
from app.schemas.history import HistoryDetail, HistoryItem, HistoryListResponse

router = APIRouter(prefix="/history", tags=["历史记录"])


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    task_ids: list[str]


class FavoriteResponse(BaseModel):
    """收藏响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    result_id: str
    favorite: bool


@router.get("", response_model=ApiResponse[HistoryListResponse])
async def list_history(
    user: CurrentUser,
    service: HistoryServiceDep,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    favorite: bool = Query(default=False, description="仅查看含收藏结果的记录"),
) -> ApiResponse[HistoryListResponse]:
    """分页获取用户历史任务列表；favorite=true 时仅返回含收藏结果的记录"""
    result = await service.list_history(
        user.user_id, page=page, page_size=page_size, favorite=favorite
    )
    return ApiResponse.success(data=result)


# -------------------- 固定路径（须在动态路径前） --------------------

@router.get("/favorites", response_model=ApiResponse[HistoryListResponse])
async def list_favorites(
    user: CurrentUser,
    service: HistoryServiceDep,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
) -> ApiResponse[HistoryListResponse]:
    """获取收藏列表（复用列表响应结构）"""
    # 通过历史服务所在会话查询收藏
    favorites = await service.repo.get_favorites(
        user.user_id, offset=(page - 1) * page_size, limit=page_size
    )

    items: list[HistoryItem] = []
    for r in favorites:
        items.append(
            HistoryItem(
                task_id=r.task_id,
                skill_id=r.skill_id,
                provider=r.provider,
                image_id=r.image_id,
                original_url="",
                status="success",
                result_thumbnails=[r.thumbnail_url or r.result_url],
                has_favorite=True,
                created_at=r.created_at,
            )
        )

    # 注：此处 total 为当前页返回条数；如需精确总数可在仓储层补充 count 方法
    return ApiResponse.success(
        data=HistoryListResponse(
            total=len(items), page=page, page_size=page_size, items=items
        )
    )


@router.delete("/batch", response_model=ApiResponse[int], status_code=status.HTTP_200_OK)
async def batch_delete(
    payload: BatchDeleteRequest,
    user: CurrentUser,
    service: HistoryServiceDep,
) -> ApiResponse[int]:
    """批量删除结果"""
    deleted = await service.batch_delete(user.user_id, payload.task_ids)
    return ApiResponse.success(data=deleted, message=f"已删除 {deleted} 条")


# -------------------- 动态路径 --------------------

@router.get("/{result_id}", response_model=ApiResponse[HistoryDetail])
async def get_history_detail(
    result_id: str,
    user: CurrentUser,
    service: HistoryServiceDep,
) -> ApiResponse[HistoryDetail]:
    """获取结果详情"""
    result = await service.repo.get_result(result_id)
    if result is None:
        from app.core.exceptions import NotFoundException

        raise NotFoundException(f"结果 [{result_id}] 不存在")
    if result.user_id != user.user_id:
        from app.core.exceptions import ForbiddenException

        raise ForbiddenException("无权访问该结果")
    detail = await service.detail(user.user_id, result.task_id)
    return ApiResponse.success(data=detail)


@router.delete("/{task_id}", response_model=ApiResponse[bool])
async def delete_history(
    task_id: str,
    user: CurrentUser,
    service: HistoryServiceDep,
) -> ApiResponse[bool]:
    """删除单条任务及其关联结果"""
    ok = await service.delete(user.user_id, task_id)
    return ApiResponse.success(data=ok, message="删除成功")


@router.post("/{result_id}/favorite", response_model=ApiResponse[FavoriteResponse])
async def toggle_favorite(
    result_id: str,
    user: CurrentUser,
    service: HistoryServiceDep,
    favorite: bool | None = Query(default=None, description="收藏状态，缺省取反"),
) -> ApiResponse[FavoriteResponse]:
    """切换或设置收藏状态"""
    new_state = await service.favorite(user.user_id, result_id, favorite)
    return ApiResponse.success(
        data=FavoriteResponse(result_id=result_id, favorite=new_state),
        message="已收藏" if new_state else "已取消收藏",
    )
