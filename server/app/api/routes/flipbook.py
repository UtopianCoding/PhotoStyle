"""
3D 翻页画册路由

提供画册的 CRUD 接口。
"""

import re
from urllib.parse import quote

from fastapi import APIRouter, Query, Response
from fastapi.responses import PlainTextResponse

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import ApiResponse
from app.schemas.flipbook import (
    CreateFlipbookRequest,
    FlipbookListResponse,
    FlipbookPageRead,
    FlipbookProjectRead,
)
from app.services.flipbook_export_service import FlipbookExportService
from app.services.flipbook_service import FlipbookService
from app.services.model_config_store import model_config_store

router = APIRouter(prefix="/flipbook", tags=["3D翻页画册"])


@router.get("/bgm", response_model=ApiResponse[dict])
async def get_bgm_config(
    _: CurrentUser,
) -> ApiResponse[dict]:
    """获取背景音乐 URL（空字符串表示使用内置 mp3）"""
    return ApiResponse.success(
        data={"musicUrl": model_config_store.get_bgm_music_url()},
        message="ok",
    )


@router.get("/photos", response_model=ApiResponse[list])
async def list_available_photos(
    user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=200, ge=1, le=500, description="最大返回数量"),
) -> ApiResponse[list]:
    """获取用户可用的转换结果照片列表"""
    service = FlipbookService(db)
    photos = await service.list_available_photos(user.user_id, limit=limit)
    return ApiResponse.success(data=photos)


@router.get("/{project_id}/download")
async def download_flipbook(
    project_id: str,
    user: CurrentUser,
    db: DBSession,
) -> Response:
    """下载画册为静态 HTML 网页（含 3D 翻页效果）"""
    service = FlipbookExportService(db)
    html_doc = await service.export_html(user.user_id, project_id)
    # 从标题中提取文件名（可能含中文），去掉导出的 " - 3D 相册" 后缀
    filename = "photo-book.html"
    match = re.search(r"<title>(.*?)</title>", html_doc)
    if match:
        raw_title = re.sub(r"\s*-\s*3D\s*相册\s*$", "", match.group(1))
        safe = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", raw_title).strip("-")[:40]
        if safe:
            filename = f"{safe}.html"
    # 中文文件名需用 RFC 5987 filename*（UTF-8 编码），同时提供 ASCII 回退名
    ascii_name = re.sub(r"[^\x20-\x7e]", "_", filename) or "photo-book.html"
    disposition = (
        f'attachment; filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return PlainTextResponse(
        content=html_doc,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": disposition},
    )


@router.post("", response_model=ApiResponse[FlipbookProjectRead])
async def create_flipbook(
    payload: CreateFlipbookRequest,
    user: CurrentUser,
    db: DBSession,
) -> ApiResponse[FlipbookProjectRead]:
    """创建画册"""
    service = FlipbookService(db)
    result = await service.create_flipbook(user.user_id, payload)
    return ApiResponse.success(data=result, message="画册创建成功")


@router.get("", response_model=ApiResponse[FlipbookListResponse])
async def list_flipbooks(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
) -> ApiResponse[FlipbookListResponse]:
    """分页获取用户画册列表"""
    service = FlipbookService(db)
    result = await service.list_flipbooks(user.user_id, page=page, page_size=page_size)
    return ApiResponse.success(data=result)


@router.get("/{project_id}", response_model=ApiResponse[FlipbookProjectRead])
async def get_flipbook(
    project_id: str,
    user: CurrentUser,
    db: DBSession,
) -> ApiResponse[FlipbookProjectRead]:
    """获取画册详情"""
    service = FlipbookService(db)
    result = await service.get_flipbook(user.user_id, project_id)
    return ApiResponse.success(data=result)


@router.delete("/{project_id}", response_model=ApiResponse[bool])
async def delete_flipbook(
    project_id: str,
    user: CurrentUser,
    db: DBSession,
) -> ApiResponse[bool]:
    """删除画册"""
    service = FlipbookService(db)
    ok = await service.delete_flipbook(user.user_id, project_id)
    return ApiResponse.success(data=ok, message="画册已删除")


@router.post("/{project_id}/regenerate", response_model=ApiResponse[FlipbookProjectRead])
async def regenerate_flipbook(
    project_id: str,
    user: CurrentUser,
    db: DBSession,
) -> ApiResponse[FlipbookProjectRead]:
    """重新生成画册的 AI 内容（主题色和 caption）"""
    service = FlipbookService(db)
    result = await service.regenerate_flipbook(user.user_id, project_id)
    return ApiResponse.success(data=result, message="画册重新生成已启动")


@router.put("/{project_id}/pages/{page_id}", response_model=ApiResponse[FlipbookPageRead])
async def update_page(
    project_id: str,
    page_id: str,
    user: CurrentUser,
    db: DBSession,
    caption: str | None = None,
    text: str | None = None,
    fit: str | None = None,
) -> ApiResponse[FlipbookPageRead]:
    """更新画册页面信息"""
    service = FlipbookService(db)
    result = await service.update_page(
        user.user_id, project_id, page_id, caption=caption, text=text, fit=fit
    )
    return ApiResponse.success(data=result, message="页面已更新")
