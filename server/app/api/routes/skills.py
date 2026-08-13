"""
技能相关路由

提供可用技能列表查询。
"""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.core.skill_engine import SkillConfig, SkillEngine
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/skills", tags=["技能"])


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
    # 预览图 URL
    preview: str = ""
    # 技能分类
    category: str = "默认"


@router.get("", response_model=ApiResponse[list[SkillSummary]])
async def list_skills() -> ApiResponse[list[SkillSummary]]:
    """列出所有可用技能"""
    engine = SkillEngine()
    skills = engine.list_skills()
    summaries = [
        SkillSummary(
            id=s.skill_id,
            name=s.name,
            description=s.description,
            provider=s.provider,
            ratio=s.ratio,
            subject_ratio=s.subject_ratio,
            preview=(
                f"/api/v1/skills/assets/{s.skill_id}/{s.preview}"
                if s.preview
                else ""
            ),
        )
        for s in skills
    ]
    return ApiResponse.success(data=summaries)
