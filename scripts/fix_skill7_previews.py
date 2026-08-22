"""
修复 scenes-gathered-zine 技能的预览图

将本地的 skill7/01.jpg 和 skill7/02.jpg 压缩后上传到 MinIO，
并更新数据库中的 preview_urls 字段。
"""

import asyncio
import io
import json
import os
import sys
from pathlib import Path
from PIL import Image

# 添加 server 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

from sqlalchemy import select, update
from app.database import async_session_maker
from app.models.skill_config import SkillConfig
from app.core.storage import get_storage_provider


def compress_image(img_path: Path, max_width: int = 1200, quality: int = 85) -> bytes:
    """压缩图片，返回压缩后的字节"""
    img = Image.open(img_path)
    original_size = img_path.stat().st_size
    
    # 转换为 RGB（JPEG 不支持透明通道）
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    
    # 调整尺寸
    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        print(f"  尺寸缩放: {img.width}x{img.height} -> {new_size[0]}x{new_size[1]}")
    
    # 压缩保存
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=quality, optimize=True)
    compressed = buffer.getvalue()
    
    print(f"  压缩: {original_size // 1024}KB -> {len(compressed) // 1024}KB ({len(compressed) * 100 // original_size}%)")
    
    # 如果压缩后更大，使用原始文件
    if len(compressed) >= original_size:
        print("  压缩后更大，使用原始文件")
        return img_path.read_bytes()
    
    return compressed


async def fix_skill7_previews():
    """修复 scenes-gathered-zine 的预览图"""
    
    # 检查本地文件
    skill7_dir = Path(__file__).parent.parent / "web" / "src" / "skill7"
    image_files = ["01.jpg", "02.jpg"]
    
    print(f"检查本地文件: {skill7_dir}")
    for img in image_files:
        img_path = skill7_dir / img
        if not img_path.exists():
            print(f"[错误] 文件不存在: {img_path}")
            return
        print(f"[OK] 找到文件: {img_path} ({img_path.stat().st_size // 1024}KB)")
    
    # 压缩并上传到 MinIO
    print("\n压缩并上传到 MinIO...")
    storage = get_storage_provider()
    uploaded_urls = []
    
    for img in image_files:
        img_path = skill7_dir / img
        
        # 压缩图片
        print(f"\n压缩 {img}:")
        compressed_bytes = compress_image(img_path)
        
        # 生成对象键
        object_key = f"skill-previews/scenes-gathered-zine/{img}"
        
        try:
            url = await asyncio.to_thread(
                storage.upload,
                object_key,
                compressed_bytes,
                "image/jpeg"
            )
            print(f"[OK] 已上传: {img} -> {url}")
            uploaded_urls.append(url)
        except Exception as e:
            print(f"[错误] 上传失败 {img}: {e}")
            return
    
    # 更新数据库
    print("\n更新数据库...")
    async with async_session_maker() as db:
        # 查询技能
        stmt = select(SkillConfig).where(SkillConfig.skill_id == "scenes-gathered-zine")
        result = await db.execute(stmt)
        skill = result.scalar_one_or_none()
        
        if not skill:
            print("[错误] 数据库中未找到 scenes-gathered-zine 技能")
            return
        
        print(f"[OK] 找到技能: {skill.name}")
        
        # 更新 preview_urls
        preview_urls_json = json.dumps(uploaded_urls)
        skill.preview_urls = preview_urls_json
        skill.preview_url = uploaded_urls[0] if uploaded_urls else None
        
        await db.commit()
        
        print(f"[OK] 已更新 preview_url: {skill.preview_url}")
        print(f"[OK] 已更新 preview_urls: {preview_urls_json}")
    
    print("\n[完成] 预览图已修复！")


if __name__ == "__main__":
    asyncio.run(fix_skill7_previews())
