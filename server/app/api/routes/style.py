"""
风格转换相关路由

提供图片分析、转换入口、任务状态查询与任务取消接口。
"""

from fastapi import APIRouter, BackgroundTasks, status

from app.api.deps import CurrentUser, DBSession, StyleServiceDep
from app.schemas.common import ApiResponse
from app.schemas.style import (
    AnalyzeRequest,
    AnalyzeResponse,
    ConvertRequest,
    ConvertResponse,
    TaskStatusResponse,
)
from app.services.style_service import process_style_task

router = APIRouter(prefix="/style", tags=["风格转换"])


@router.post("/analyze", response_model=ApiResponse[AnalyzeResponse])
async def analyze(
    payload: AnalyzeRequest,
    user: CurrentUser,
    service: StyleServiceDep,
) -> ApiResponse[AnalyzeResponse]:
    """
    分析图片，生成结构化提示词 + 诗意小字选项。

    调用 VL 模型深度分析照片，返回：
    - 主体识别（人物、场景、氛围等）
    - 核心保留元素
    - 插画规则（构图、色彩、风格等）
    - 最终英文提示词（直接可用于 AI 图像生成）
    - 5 个诗意小字备选

    用户可选择诗意小字后，再调用 /style/convert 发起转换。
    """
    response = await service.analyze(user.user_id, payload)
    return ApiResponse.success(data=response, message="分析完成")


@router.post("/convert", response_model=ApiResponse[ConvertResponse], status_code=status.HTTP_202_ACCEPTED)
async def convert(
    payload: ConvertRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    service: StyleServiceDep,
) -> ApiResponse[ConvertResponse]:
    """
    发起风格转换。

    如果提供了 finalPrompt（来自 /style/analyze 的分析结果），
    则跳过后台分析阶段，直接使用该提示词进行图像生成。
    创建 pending 任务后立即返回 task_id；真正的生成流程在后台异步执行，
    客户端通过 GET /style/tasks/{task_id} 轮询状态。
    """
    response = await service.convert(user.user_id, payload)
    # 任务创建成功后，将完整生成流程交给后台任务执行
    background_tasks.add_task(process_style_task, response.task_id)
    return ApiResponse.success(data=response, message="任务已创建")


@router.get("/tasks/{task_id}", response_model=ApiResponse[TaskStatusResponse])
async def get_task_status(
    task_id: str,
    user: CurrentUser,
    service: StyleServiceDep,
) -> ApiResponse[TaskStatusResponse]:
    """查询任务状态与结果"""
    status_resp = await service.get_task_status(user.user_id, task_id)
    return ApiResponse.success(data=status_resp)


@router.post("/tasks/{task_id}/cancel", response_model=ApiResponse[TaskStatusResponse])
async def cancel_task(
    task_id: str,
    user: CurrentUser,
    service: StyleServiceDep,
) -> ApiResponse[TaskStatusResponse]:
    """取消任务"""
    status_resp = await service.cancel_task(user.user_id, task_id)
    return ApiResponse.success(data=status_resp, message="任务已取消")


@router.get("/public/tasks/{task_id}", response_model=ApiResponse[TaskStatusResponse])
async def get_public_task_status(
    task_id: str,
    service: StyleServiceDep,
) -> ApiResponse[TaskStatusResponse]:
    """
    公开查看任务结果（无需登录，用于分享海报扫码查看）。

    仅返回任务状态和图片信息，不暴露用户敏感数据。
    """
    status_resp = await service.get_public_task_status(task_id)
    return ApiResponse.success(data=status_resp)
