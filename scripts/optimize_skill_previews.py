"""
优化 scenes-gathered-zine 技能的预览图
生成压缩后的缩略图并上传到 MinIO，然后更新数据库
"""

import json
from pathlib import Path
from PIL import Image
import io
import sys

print("脚本开始执行...")
print(f"Python 版本: {sys.version}")
print(f"当前目录: {Path.cwd()}")
sys.stdout.flush()

# 添加 server 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'server'))

# 1. 生成缩略图并上传
print("\n=== 步骤1: 生成缩略图并上传 ===")
sys.stdout.flush()

skill7_dir = Path(__file__).parent.parent / 'web' / 'src' / 'skill7'
print(f"图片目录: {skill7_dir}")
print(f"目录存在: {skill7_dir.exists()}")
sys.stdout.flush()

if not skill7_dir.exists():
    print("错误: 目录不存在")
    sys.exit(1)

from app.core.storage import get_storage_provider

print("初始化存储提供者...")
sys.stdout.flush()
storage = get_storage_provider()
print("存储提供者已初始化")
sys.stdout.flush()

new_preview_urls = []

for i, original_file in enumerate(['01.jpg', '02.jpg'], 1):
    original_path = skill7_dir / original_file
    
    if not original_path.exists():
        print(f"跳过: {original_file} 不存在")
        continue
    
    file_size_mb = original_path.stat().st_size / 1024 / 1024
    print(f"\n处理: {original_file} ({file_size_mb:.2f} MB)")
    sys.stdout.flush()
    
    # 打开并压缩图片
    with Image.open(original_path) as img:
        # 转换为 RGB（去除 alpha 通道）
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        original_size = img.size
        print(f"  原始尺寸: {original_size[0]}x{original_size[1]}")
        
        # 调整大小（保持宽高比，最大宽度 800px）
        max_width = 800
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            print(f"  调整后尺寸: {img.width}x{img.height}")
        
        # 压缩为 JPEG（质量 85%）
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
        img_bytes = img_byte_arr.getvalue()
        
        print(f"  压缩后大小: {len(img_bytes) / 1024:.1f} KB")
    
    # 上传到 MinIO
    thumbnail_key = f"skill-previews/scenes-gathered-zine/0{i}_thumb.jpg"
    print(f"  上传到 MinIO: {thumbnail_key}")
    sys.stdout.flush()
    thumbnail_url = storage.upload(thumbnail_key, img_bytes, "image/jpeg")
    
    print(f"  上传成功: {thumbnail_url}")
    new_preview_urls.append(thumbnail_url)
    sys.stdout.flush()

# 2. 更新数据库
print("\n=== 步骤2: 更新数据库 ===")
sys.stdout.flush()

import pymysql
from app.config import settings

# 解析数据库连接字符串
db_url = settings.database.url
# 格式: mysql+aiomysql://user:password@host:port/database
parts = db_url.replace('mysql+aiomysql://', '').split('@')
user_pass = parts[0].split(':')
host_port_db = parts[1].split('/')
host_port = host_port_db[0].split(':')

user = user_pass[0]
password = user_pass[1]
host = host_port[0]
port = int(host_port[1]) if len(host_port) > 1 else 3306
database = host_port_db[1]

print(f"连接数据库: {host}:{port}/{database}")
sys.stdout.flush()

conn = pymysql.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    database=database,
    charset='utf8mb4'
)

try:
    with conn.cursor() as cursor:
        # 更新 preview_urls
        preview_urls_json = json.dumps(new_preview_urls)
        sql = "UPDATE skill_configs SET preview_urls = %s WHERE skill_id = %s"
        cursor.execute(sql, (preview_urls_json, 'scenes-gathered-zine'))
        conn.commit()
        print(f"数据库已更新，影响行数: {cursor.rowcount}")
        sys.stdout.flush()
        
        # 验证更新
        cursor.execute("SELECT preview_urls FROM skill_configs WHERE skill_id = %s", ('scenes-gathered-zine',))
        result = cursor.fetchone()
        if result:
            urls = json.loads(result[0])
            print(f"\n验证结果，共 {len(urls)} 张缩略图:")
            for url in urls:
                print(f"  - {url}")
finally:
    conn.close()

print("\n=== 完成 ===")
print(f"共处理 {len(new_preview_urls)} 张图片")
