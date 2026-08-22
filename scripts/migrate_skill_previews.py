"""
迁移技能预览图脚本

将 web/src/skill1~skill7 目录下的预览图上传到对象存储，
并更新数据库 skill_configs 表的 preview_urls 字段。

运行方式: python -m scripts.migrate_skill_previews
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加 server 目录到 Python 路径
server_dir = Path(__file__).parent.parent / "server"
sys.path.insert(0, str(server_dir))

from app.core.storage import get_storage_provider
from app.database import async_session_maker
from app.models.skill_config import SkillConfig
from sqlalchemy import select, update

# 技能预览图映射（从 web/src/constants/skillImages.ts 提取）
SKILL_PREVIEW_MAP = {
    "photo-revival": [
        "skill1/01_car_page_thumb.jpg",
        "skill1/01_moon_gate_thumb.jpg",
        "skill1/03_pagoda_thumb.jpg",
        "skill1/06_mask_dance_thumb.jpg",
    ],
    "city-editorial": [
        "skill2/1_thumb.jpg",
        "skill2/2_thumb.jpg",
        "skill2/3_thumb.jpg",
        "skill2/4_thumb.jpg",
    ],
    "photo-abstract-editorial": [
        "skill3/case-1_thumb.jpg",
        "skill3/case-2_thumb.jpg",
        "skill3/case-4_thumb.jpg",
        "skill3/case-6_thumb.jpg",
    ],
    "fridge-magnet": [
        "skill4/01_thumb.jpg",
        "skill4/02_thumb.jpg",
    ],
    "ink-minimalist": [
        "skill5/1_thumb.jpg",
        "skill5/2_thumb.jpg",
        "skill5/3_thumb.jpg",
        "skill5/4_thumb.jpg",
    ],
    "marker-child-doodle": [
        "skill6/reference-01_thumb.jpg",
    ],
    "scenes-gathered-zine": [
        "skill7/01.jpg",
        "skill7/02.jpg",
    ],
}


async def migrate_previews():
    """迁移预览图到对象存储并更新数据库"""
    web_dir = Path(__file__).parent.parent / "web" / "src"
    storage = get_storage_provider()
    
    # 存储已上传的 URL
    uploaded_urls = {}
    
    print("=" * 60)
    print("开始迁移技能预览图")
    print("=" * 60)
    
    # 上传所有预览图
    for skill_id, preview_files in SKILL_PREVIEW_MAP.items():
        print(f"\n处理技能: {skill_id}")
        urls = []
        
        for preview_file in preview_files:
            file_path = web_dir / preview_file
            
            if not file_path.exists():
                print(f"  [警告] 文件不存在: {preview_file}")
                continue
            
            # 生成对象存储 key
            object_key = f"skill-previews/{skill_id}/{file_path.name}"
            
            # 检查是否已上传
            try:
                # 读取文件
                with open(file_path, "rb") as f:
                    file_data = f.read()
                
                # 上传到对象存储
                url = storage.upload(object_key, file_data, "image/jpeg")
                urls.append(url)
                print(f"  [成功] {file_path.name} -> {url}")
                
            except Exception as e:
                print(f"  [失败] {file_path.name}: {e}")
        
        uploaded_urls[skill_id] = urls
    
    # 更新数据库
    print("\n" + "=" * 60)
    print("更新数据库")
    print("=" * 60)
    
    async with async_session_maker() as session:
        for skill_id, urls in uploaded_urls.items():
            if not urls:
                print(f"\n[跳过] {skill_id}: 无可用预览图")
                continue
            
            # 查询技能配置
            result = await session.execute(
                select(SkillConfig).where(SkillConfig.skill_id == skill_id)
            )
            skill_config = result.scalar_one_or_none()
            
            if not skill_config:
                print(f"\n[警告] {skill_id}: 技能配置不存在")
                continue
            
            # 更新 preview_urls 字段
            preview_urls_json = json.dumps(urls, ensure_ascii=False)
            await session.execute(
                update(SkillConfig)
                .where(SkillConfig.skill_id == skill_id)
                .values(preview_urls=preview_urls_json)
            )
            
            print(f"\n[成功] {skill_id}: 已更新 {len(urls)} 张预览图")
        
        # 提交事务
        await session.commit()
    
    print("\n" + "=" * 60)
    print("迁移完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(migrate_previews())
