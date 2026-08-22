"""
Add photo-relic-editorial skill to database.
"""

import asyncio
import os
import sys

# 添加 server 目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, text
from app.database import async_session_maker
from app.models.skill_config import SkillConfig


async def add_photo_relic_skill():
    """添加 photo-relic-editorial 技能到数据库"""
    
    skill_id = "photo-relic-editorial"
    name = "Photo Relic Editorial"
    description = "Create distinctive Photo Relic editorial artworks from user-provided photographs: preserve the real photo and pair it with a recognizable, artful abstract relic shaped like memory, modern printmaking, quiet Eastern restraint, and source-derived light."
    
    # 从 prompt_template.txt 读取提示词模板
    template_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "skills", skill_id, "prompt_template.txt"
    )
    with open(template_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()
    
    async with async_session_maker() as db:
        # 检查是否已存在
        result = await db.execute(
            select(SkillConfig).where(SkillConfig.skill_id == skill_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"[SKIP] Skill '{skill_id}' already exists in database")
            print(f"  name: {existing.name}")
            print(f"  is_active: {existing.is_active}")
            return
        
        # 创建新技能配置
        skill = SkillConfig(
            skill_id=skill_id,
            name=name,
            description=description,
            prompt_template=prompt_template,
            provider="qianwen",
            ratio="3:4",
            subject_ratio="10-16%",
            category="editorial",
            preview_url="",
            preview_urls="[]",
            is_active=True,
            need_analysis=True,
            sort_order=15,  # 排在 city-editorial(20) 之前
        )
        
        db.add(skill)
        await db.commit()
        
        print(f"[OK] Added skill '{skill_id}' to database")
        print(f"  name: {name}")
        print(f"  sort_order: 15")
        print(f"  need_analysis: True")
        print(f"  is_active: True")


if __name__ == "__main__":
    import sys
    result = asyncio.run(add_photo_relic_skill())
    sys.stdout.flush()
    sys.stderr.flush()
