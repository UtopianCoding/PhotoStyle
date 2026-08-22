# ---------- Python 3.11 后端 ----------
FROM python:3.11-slim

WORKDIR /app

# 换国内 Debian 源（阿里云镜像），加速 apt 下载
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖（Pillow 编译需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY . .

EXPOSE 7823

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7823"]
