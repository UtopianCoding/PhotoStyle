"""
技能配置管理路由

提供技能配置的增删改查接口，所有路由仅管理员可访问。
"""

import json
import logging
import uuid

from fastapi import APIRouter, File, UploadFile
from sqlalchemy import select

from app.api.deps import AdminUser, DBSession
from app.core.exceptions import NotFoundException, ValidationException
from app.models.skill_config import SkillConfig
from app.schemas.common import ApiResponse
from app.schemas.skill_config import (
    SkillConfigCreate,
    SkillConfigListResponse,
    SkillConfigResponse,
    SkillConfigUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/skills", tags=["技能管理"])


def _to_response(skill: SkillConfig) -> SkillConfigResponse:
    """将 ORM 模型转换为响应模型"""
    # 解析 preview_urls JSON 字符串为列表
    preview_urls = []
    if skill.preview_urls:
        try:
            preview_urls = json.loads(skill.preview_urls)
        except (json.JSONDecodeError, TypeError):
            preview_urls = []
    
    return SkillConfigResponse(
        id=skill.id,
        skill_id=skill.skill_id,
        name=skill.name,
        description=skill.description,
        prompt_template=skill.prompt_template,
        provider=skill.provider,
        ratio=skill.ratio,
        subject_ratio=skill.subject_ratio,
        category=skill.category,
        preview_url=skill.preview_url,
        preview_urls=preview_urls,
        is_active=skill.is_active,
        need_analysis=skill.need_analysis,
        sort_order=skill.sort_order,
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


@router.get("", response_model=ApiResponse[SkillConfigListResponse])
async def list_skill_configs(
    _: AdminUser,
    db: DBSession,
) -> ApiResponse[SkillConfigListResponse]:
    """获取所有技能配置列表"""
    stmt = select(SkillConfig).order_by(SkillConfig.sort_order.asc(), SkillConfig.id.asc())
    result = await db.execute(stmt)
    skills = result.scalars().all()

    items = [_to_response(s) for s in skills]
    data = SkillConfigListResponse(items=items, total=len(items))
    return ApiResponse.success(data=data, message="ok")


@router.get("/{skill_id}", response_model=ApiResponse[SkillConfigResponse])
async def get_skill_config(
    skill_id: str,
    _: AdminUser,
    db: DBSession,
) -> ApiResponse[SkillConfigResponse]:
    """获取单个技能配置详情"""
    stmt = select(SkillConfig).where(SkillConfig.skill_id == skill_id)
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()

    if skill is None:
        raise NotFoundException(f"技能 [{skill_id}] 不存在")

    return ApiResponse.success(data=_to_response(skill), message="ok")


@router.post("", response_model=ApiResponse[SkillConfigResponse])
async def create_skill_config(
    _: AdminUser,
    payload: SkillConfigCreate,
    db: DBSession,
) -> ApiResponse[SkillConfigResponse]:
    """创建新技能配置"""
    # 检查 skill_id 是否已存在
    stmt = select(SkillConfig).where(SkillConfig.skill_id == payload.skill_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        raise ValidationException(f"技能ID [{payload.skill_id}] 已存在")

    # 创建新技能
    # 将 preview_urls 列表转换为 JSON 字符串
    preview_urls_json = None
    if payload.preview_urls:
        preview_urls_json = json.dumps(payload.preview_urls)
    
    skill = SkillConfig(
        skill_id=payload.skill_id,
        name=payload.name,
        description=payload.description,
        prompt_template=payload.prompt_template,
        provider=payload.provider,
        ratio=payload.ratio,
        subject_ratio=payload.subject_ratio,
        category=payload.category,
        preview_url=payload.preview_url,
        preview_urls=preview_urls_json,
        is_active=payload.is_active,
        need_analysis=payload.need_analysis,
        sort_order=payload.sort_order,
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    logger.info("管理员创建技能: %s", skill.skill_id)
    return ApiResponse.success(data=_to_response(skill), message="技能创建成功")


@router.put("/{skill_id}", response_model=ApiResponse[SkillConfigResponse])
async def update_skill_config(
    skill_id: str,
    _: AdminUser,
    payload: SkillConfigUpdate,
    db: DBSession,
) -> ApiResponse[SkillConfigResponse]:
    """更新技能配置"""
    stmt = select(SkillConfig).where(SkillConfig.skill_id == skill_id)
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()

    if skill is None:
        raise NotFoundException(f"技能 [{skill_id}] 不存在")

    # 更新字段
    update_data = payload.model_dump(exclude_unset=True)
    
    # 特殊处理 preview_urls：将列表转换为 JSON 字符串
    if 'preview_urls' in update_data:
        preview_urls_value = update_data['preview_urls']
        if preview_urls_value:
            update_data['preview_urls'] = json.dumps(preview_urls_value)
        else:
            update_data['preview_urls'] = None
    
    for field, value in update_data.items():
        setattr(skill, field, value)

    await db.commit()
    await db.refresh(skill)

    logger.info("管理员更新技能: %s", skill_id)
    return ApiResponse.success(data=_to_response(skill), message="技能更新成功")


@router.delete("/{skill_id}", response_model=ApiResponse)
async def delete_skill_config(
    skill_id: str,
    _: AdminUser,
    db: DBSession,
) -> ApiResponse:
    """删除技能配置"""
    stmt = select(SkillConfig).where(SkillConfig.skill_id == skill_id)
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()

    if skill is None:
        raise NotFoundException(f"技能 [{skill_id}] 不存在")

    await db.delete(skill)
    await db.commit()

    logger.info("管理员删除技能: %s", skill_id)
    return ApiResponse.success(message="技能删除成功")


@router.post("/upload-preview", response_model=ApiResponse[dict])
async def upload_skill_preview(
    _: AdminUser,
    file: UploadFile = File(..., description="预览图文件"),
) -> ApiResponse[dict]:
    """
    上传技能预览图。

    返回上传后的图片 URL，可用于设置 preview_url 字段。
    图片会自动压缩以优化加载性能。
    """
    import asyncio
    import io
    from PIL import Image

    from app.core.storage import get_storage_provider

    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise ValidationException("只允许上传图片文件")

    # 读取文件内容
    file_bytes = await file.read()

    # 限制原始文件大小（10MB）
    max_size = 10 * 1024 * 1024
    if len(file_bytes) > max_size:
        raise ValidationException(f"图片大小不能超过 10MB，当前 {len(file_bytes) // 1024}KB")

    # 压缩图片
    try:
        img = Image.open(io.BytesIO(file_bytes))
        
        # 转换为 RGB 模式（如果需要）
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            # 保持透明通道用于 PNG/WebP
            if file.content_type and ('png' in file.content_type or 'webp' in file.content_type):
                pass
            else:
                img = img.convert('RGB')
        
        # 调整尺寸：最大宽度 1200px，保持宽高比
        max_width = 1200
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"图片已缩放: {img.width}x{img.height} -> {new_size[0]}x{new_size[1]}")
        
        # 确定输出格式和压缩参数
        output_format = 'JPEG'
        output_ext = 'jpg'
        output_content_type = 'image/jpeg'
        quality = 85
        
        if file.content_type:
            if 'png' in file.content_type:
                output_format = 'PNG'
                output_ext = 'png'
                output_content_type = 'image/png'
                quality = 85  # PNG 的压缩级别
            elif 'webp' in file.content_type:
                output_format = 'WEBP'
                output_ext = 'webp'
                output_content_type = 'image/webp'
                quality = 85
        
        # 保存到字节流
        output_buffer = io.BytesIO()
        if output_format == 'JPEG':
            img.save(output_buffer, format=output_format, quality=quality, optimize=True)
        elif output_format == 'PNG':
            img.save(output_buffer, format=output_format, optimize=True)
        elif output_format == 'WEBP':
            img.save(output_buffer, format=output_format, quality=quality)
        
        compressed_bytes = output_buffer.getvalue()
        
        # 如果压缩后反而更大，使用原始文件（对于已优化的图片）
        if len(compressed_bytes) >= len(file_bytes):
            compressed_bytes = file_bytes
            logger.info("压缩后文件更大，使用原始文件")
        else:
            logger.info(f"图片已压缩: {len(file_bytes) // 1024}KB -> {len(compressed_bytes) // 1024}KB")
            
    except Exception as e:
        logger.warning(f"图片压缩失败，使用原始文件: {e}")
        compressed_bytes = file_bytes

    # 上传到对象存储
    storage = get_storage_provider()
    file_key = f"skill-preview/{uuid.uuid4().hex}.{output_ext}"
    
    url = await asyncio.to_thread(
        storage.upload, file_key, compressed_bytes, output_content_type
    )

    logger.info("管理员上传技能预览图: %s", url)
    return ApiResponse.success(
        data={"url": url},
        message="预览图上传成功",
    )
