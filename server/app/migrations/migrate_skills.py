"""
技能数据迁移脚本

将现有的文件系统技能（SKILL.md）迁移到数据库技能管理系统中。
运行方式: python -m app.migrations.migrate_skills
"""

import asyncio
import os
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skill_engine import SKILLS_DIR
from app.database import async_session_maker
from app.models.skill_config import SkillConfig

# 技能配置：是否需要分析、排序权重
SKILL_CONFIGS = {
    "photo-revival": {
        "need_analysis": True,
        "sort_order": 10,
    },
    "city-editorial": {
        "need_analysis": True,
        "sort_order": 20,
    },
    "photo-abstract-editorial": {
        "need_analysis": True,
        "sort_order": 30,
    },
    "fridge-magnet": {
        "need_analysis": False,
        "sort_order": 40,
    },
    "ink-minimalist": {
        "need_analysis": False,
        "sort_order": 50,
    },
    "memory-postcard": {
        "need_analysis": False,
        "sort_order": 60,
    },
    "scenes-gathered-zine": {
        "need_analysis": False,
        "sort_order": 70,
    },
}


def parse_skill_md(content: str, skill_id: str) -> dict:
    """解析 SKILL.md 文件，提取 frontmatter 和 prompt 模板"""
    result = {
        "skill_id": skill_id,
        "name": skill_id,
        "description": "",
        "prompt_template": "",
        "provider": "qianwen",
        "ratio": "3:4",
        "subject_ratio": "10-16%",
        "category": "默认",
    }

    # 解析 frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
    if fm_match:
        frontmatter = fm_match.group(1)
        body = fm_match.group(2).strip()

        # 解析 frontmatter 字段
        for line in frontmatter.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key == "name":
                result["name"] = value
            elif key == "description":
                result["description"] = value
            elif key == "provider":
                result["provider"] = value
            elif key == "ratio":
                result["ratio"] = value
            elif key == "subject_ratio":
                result["subject_ratio"] = value
            elif key == "category":
                result["category"] = value

        result["prompt_template"] = body
    else:
        # 没有 frontmatter，整个内容作为 prompt
        result["prompt_template"] = content.strip()

    return result


async def migrate_skill(db: AsyncSession, skill_id: str) -> bool:
    """迁移单个技能到数据库"""
    skill_path = Path(SKILLS_DIR) / skill_id / "SKILL.md"

    if not skill_path.exists():
        print(f"[跳过] {skill_id}: SKILL.md 不存在")
        return False

    # 读取 SKILL.md
    content = skill_path.read_text(encoding="utf-8")
    skill_data = parse_skill_md(content, skill_id)

    # 检查是否已存在
    stmt = select(SkillConfig).where(SkillConfig.skill_id == skill_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        print(f"[跳过] {skill_id}: 已存在于数据库")
        return False

    # 获取额外配置
    config = SKILL_CONFIGS.get(skill_id, {})

    # 创建数据库记录
    skill_config = SkillConfig(
        skill_id=skill_data["skill_id"],
        name=skill_data["name"],
        description=skill_data["description"],
        prompt_template=skill_data["prompt_template"],
        provider=skill_data["provider"],
        ratio=skill_data["ratio"],
        subject_ratio=skill_data["subject_ratio"],
        category=skill_data["category"],
        is_active=True,
        need_analysis=config.get("need_analysis", True),
        sort_order=config.get("sort_order", 100),
    )

    db.add(skill_config)
    print(f"[成功] {skill_id}: 已迁移到数据库")
    return True


async def migrate_all_skills():
    """迁移所有技能"""
    print("=" * 60)
    print("开始迁移技能到数据库...")
    print("=" * 60)

    async with async_session_maker() as db:
        # 获取所有技能目录
        skills_dir = Path(SKILLS_DIR)
        if not skills_dir.exists():
            print(f"[错误] 技能目录不存在: {SKILLS_DIR}")
            return

        skill_ids = [
            d.name for d in skills_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        ]

        print(f"\n找到 {len(skill_ids)} 个技能目录\n")

        # 迁移每个技能
        migrated = 0
        for skill_id in sorted(skill_ids):
            if await migrate_skill(db, skill_id):
                migrated += 1

        # 提交事务
        await db.commit()

        print("\n" + "=" * 60)
        print(f"迁移完成: {migrated}/{len(skill_ids)} 个技能已迁移")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(migrate_all_skills())
