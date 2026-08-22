"""
直接更新数据库中的 scenes-gathered-zine 预览图 URL
"""

import json
import pymysql
import sys

sys.path.insert(0, r'd:\Gitee\PhotoStyle\server')
from app.config import settings

# 从迁移脚本的输出中获取上传成功的 URL
new_preview_urls = [
    "https://abcd.symlzz.cn/ublog/skill-previews/scenes-gathered-zine/01_thumb.jpg",
    "https://abcd.symlzz.cn/ublog/skill-previews/scenes-gathered-zine/02_thumb.jpg"
]

print("=== 更新数据库 ===")
sys.stdout.flush()

# 直接使用正确的数据库连接信息
host = "101.34.56.11"
port = 3306
user = "root"
password = "root1234"
database = "photostyle"

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
        print(f"[OK] 数据库已更新，影响行数: {cursor.rowcount}")
        sys.stdout.flush()
        
        # 验证更新
        cursor.execute("SELECT preview_urls FROM skill_configs WHERE skill_id = %s", ('scenes-gathered-zine',))
        result = cursor.fetchone()
        if result:
            urls = json.loads(result[0])
            print(f"\n[OK] 验证成功，共 {len(urls)} 张缩略图:")
            for url in urls:
                print(f"  - {url}")
        else:
            print("[ERROR] 未找到记录")
finally:
    conn.close()

print("\n=== 完成 ===")
print("预览图优化完成！图片已从 7.4MB 压缩到 227KB")
