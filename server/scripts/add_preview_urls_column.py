"""
运行数据库迁移：添加 preview_urls 字段
"""
import asyncio
import sys
from pathlib import Path

# 添加 server 目录到 Python 路径
server_dir = Path(__file__).parent.parent
sys.path.insert(0, str(server_dir))

from sqlalchemy import text
from app.database import engine


async def run_migration():
    async with engine.begin() as conn:
        # 检查字段是否已存在
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name='skill_configs' AND column_name='preview_urls'
        """))
        count = result.scalar()
        
        if count > 0:
            print("字段 preview_urls 已存在，跳过")
            return
        
        # 添加字段
        await conn.execute(text("""
            ALTER TABLE `skill_configs` 
            ADD COLUMN `preview_urls` TEXT NULL COMMENT '多张预览图URL(JSON数组)'
        """))
        print("成功添加 preview_urls 字段")


if __name__ == "__main__":
    asyncio.run(run_migration())
