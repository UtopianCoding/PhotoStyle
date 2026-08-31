"""
技能相关路由

提供可用技能列表查询。
"""

import os
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.core.skill_engine import SKILLS_DIR, SkillConfig, SkillEngine
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/skills", tags=["技能"])


def get_filesystem_skill_previews(skill_id: str) -> list[str]:
    """
    扫描文件系统技能目录，获取预览图 URL 列表。
    
    扫描规则：
    - 查找 skill 目录下的 preview-*.jpg/png/webp 文件
    - 按文件名排序
    - 返回对应的 API URL 列表
    """
    skill_dir = os.path.join(SKILLS_DIR, skill_id)
    if not os.path.isdir(skill_dir):
        return []
    
    preview_files = []
    for filename in sorted(os.listdir(skill_dir)):
        if filename.startswith("preview-") and filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            preview_files.append(f"/api/v1/skills/assets/{skill_id}/{filename}")
    
    return preview_files


class SkillSummary(BaseModel):
    """技能摘要（列表展示用）"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # 对外暴露的技能ID（即 skill_id，目录名）
    id: str = Field(..., description="技能ID")
    # 技能名称
    name: str
    # 技能描述
    description: str
    # 推荐 AI 提供商
    provider: str = "qianwen"
    # 默认输出比例
    ratio: str = "3:4"
    # 主体占比
    subject_ratio: str = "10-16%"
    # 预览图 URL（单张，兼容旧版）
    preview: str = ""
    # 多张预览图 URL（用于首页 2x2 网格展示）
    previews: list[str] = Field(default_factory=list, description="多张预览图URL")
    # 技能分类
    category: str = "默认"
    # 是否需要分析图片（数据库配置，默认 True）
    need_analysis: bool = True
    # 输入变量（用户需手动填写，替换提示词模板 {{KEY}} 占位符）
    input_variables: list[dict] = Field(
        default_factory=list, description="输入变量列表（key/label/placeholder/hint/required/default/translate）"
    )


@router.get("", response_model=ApiResponse[list[SkillSummary]])
async def list_skills() -> ApiResponse[list[SkillSummary]]:
    """列出所有可用技能（数据库 + 文件系统）"""
    engine = SkillEngine()
    skills = await engine.list_skills_async(include_hidden=False)

    # 隐藏的技能列表（不在前端展示，从数据库和文件系统合并后的列表中过滤）
    hidden_skills = {"marker-child-doodle"}

    summaries = []
    for s in skills:
        if s.skill_id in hidden_skills:
            continue
        
        # 构建预览图列表
        if s.source == "db" and s.preview_urls:
            # 数据库技能：使用 preview_urls
            previews = s.preview_urls
        elif s.source == "file":
            # 文件系统技能：扫描目录获取预览图
            previews = get_filesystem_skill_previews(s.skill_id)
        else:
            previews = []
        
        # 构建单张预览图（兼容旧版）
        if s.source == "db" and s.preview_url:
            preview = s.preview_url
        elif s.source == "file" and s.preview:
            preview = f"/api/v1/skills/assets/{s.skill_id}/{s.preview}"
        elif previews:
            preview = previews[0]
        else:
            preview = ""
        
        summaries.append(
            SkillSummary(
                id=s.skill_id,
                name=s.name,
                description=s.description,
                provider=s.provider,
                ratio=s.ratio,
                subject_ratio=s.subject_ratio,
                category=s.category,
                preview=preview,
                previews=previews,
                need_analysis=s.need_analysis,
                input_variables=[v.to_dict() for v in (s.input_variables or [])],
            )
        )
    
    return ApiResponse.success(data=summaries)
