# PhotoStyle Docker Compose 部署指南

## 环境要求

- **操作系统**：Linux (CentOS 7+/Ubuntu 18.04+) 或 Windows Server
- **Docker**：20.10+
- **Docker Compose**：v2.x
- **已运行服务**：MySQL 8.0、Redis 6+、MinIO（宿主机上提前装好）

---

## 一、服务器准备

### 1.1 安装 Docker & Docker Compose

**Ubuntu/Debian：**
```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
docker compose version
```

**CentOS/RHEL：**
```bash
sudo yum install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
docker compose version
```

**Windows Server：** 下载安装 [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)

### 1.2 确保宿主机已有 MySQL/Redis/MinIO

如果还没装，下面给出快速拉起命令（供参考）：

```bash
# MySQL 8.0
docker run -d --name photostyle-mysql \
  -e MYSQL_ROOT_PASSWORD=root1234 \
  -e MYSQL_DATABASE=photo_style \
  -p 3306:3306 \
  -v mysql_data:/var/lib/mysql \
  mysql:8.0

# Redis
docker run -d --name photostyle-redis \
  -e REDIS_REQUIRES_PASS=yes \
  -p 6379:6379 \
  redis:7-alpine --requirepass eqaxf241

# MinIO
docker run -d --name photostyle-minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=utopian \
  -e MINIO_ROOT_PASSWORD=eqaxf241 \
  -v minio_data:/data \
  minio/minio server /data --console-address ":9001"
```

---

## 二、配置环境变量

### 2.1 复制并编辑 `.env.docker`

```bash
cd /path/to/blog        # 切换到 PhotoStyle 项目目录
cp .env.docker.example .env.docker
```

### 2.2 修改 `.env.docker` 关键配置

用编辑器打开 `.env.docker`，按实际情况修改以下字段：

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| `DATABASE_URL` | MySQL 连接串 | `mysql+aiomysql://root:root1234@host.docker.internal:3306/photo_style` |
| `REDIS_URL` | Redis 密码 | `redis://:eqaxf241@host.docker.internal:6379/0` |
| `MINIO_ENDPOINT` | MinIO 公网地址 | `your-server-ip:9000` |
| `MINIO_PUBLIC_BASE_URL` | MinIO 文件访问 URL | `http://your-server-ip:9000` |
| `MINIO_ACCESS_KEY` | MinIO Access Key | `utopian` |
| `MINIO_SECRET_KEY` | MinIO Secret Key | `eqaxf241` |
| `MINIO_BUCKET` | 桶名 | `photostyle` |
| `DASHSCOPE_API_KEY` | 千问 API Key | `sk-xxxxxxxxxxxxx` |
| `CORS_ALLOWED_ORIGINS` | 前端域名/IP | `http://your-server-ip:7821,http://your-server-ip` |
| `JWT_SECRET_KEY` | JWT 密钥（改随机字符串） | `a3b8f2c9d1e4f5a6b7c8d9e0f1a2b3c4` |

> ⚠️ **注意**：数据库和 Redis 使用 `host.docker.internal` 作为 host（容器访问宿主机的特殊域名）。如果宿主机 IP 已知，也可以替换为宿主机内网 IP（如 `192.168.1.100`），部分系统下更稳定。

---

## 三、构建并启动服务

### 3.1 一键构建 + 启动

```bash
docker compose up -d --build
```

- `--build`：首次必须加，会编译前端 Vite 构建 + 后端 Python 镜像
- `-d`：后台运行

### 3.2 查看状态

```bash
docker compose ps
```

预期输出：

```
NAME                    STATUS         PORTS
photostyle-backend      Up (healthy)   0.0.0.0:7823->7823/tcp
photostyle-web          Up             0.0.0.0:7821->80/tcp
```

### 3.3 查看日志

```bash
# 全部日志
docker compose logs -f

# 只看某个服务
docker compose logs -f backend
docker compose logs -f web
```

---

## 四、验证部署

### 4.1 直接端口访问测试

在浏览器中访问：

- **前端**：`http://你的服务器IP:7821`
- **后端 API**：`http://你的服务器IP:7823/docs` （会自动生成 Swagger 文档）

### 4.2 健康检查

```bash
# 后端健康检查
curl http://localhost:7823/api/v1/health

# 前端静态文件
curl http://localhost:7821/index.html
```

---

## 五、Nginx 反向代理（推荐）

为了让用户通过域名访问且前后端统一端口，需要在服务器上配 Nginx 反向代理。

### 5.1 创建配置文件

```bash
sudo vim /etc/nginx/conf.d/photostyle.conf
```

内容如下（按需修改域名）：

```nginx
server {
    listen 80;
    server_name your-domain.com;   # 改成你的域名或留空匹配所有

    # ---------- 前端静态资源 ----------
    location / {
        proxy_pass http://127.0.0.1:7821;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # ---------- 后端 API ----------
    location /api/ {
        proxy_pass http://127.0.0.1:7823/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSocket 支持（如果后续需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 5.2 测试并重载 Nginx

```bash
sudo nginx -t              # 检查语法
sudo systemctl reload nginx
```

现在用户可以通过 `http://your-domain.com` 直接访问，无需带端口号。

---

## 六、日常运维命令

| 操作 | 命令 |
|------|------|
| 重启所有服务 | `docker compose restart` |
| 只重启后端 | `docker compose restart backend` |
| 更新代码后重新构建 | `docker compose up -d --build` |
| 进入后端容器 | `docker exec -it photostyle-backend bash` |
| 查看磁盘占用 | `docker system df` |
| 清理无用镜像/容器 | `docker system prune -af` |
| 停止所有服务 | `docker compose down` |
| 停止 + 删除数据卷 | `docker compose down -v` |

---

## 七、常见问题排查

### Q1：后端启动失败

```bash
docker compose logs backend | tail -50
```

常见原因：
- 数据库连接失败 → 检查 `DATABASE_URL` 中的 IP/密码是否正确
- MinIO 连不上 → 检查 `MINIO_ENDPOINT` 是否可访问

### Q2：前端页面空白

- 检查浏览器控制台是否有 CORS 错误 → 调整 `CORS_ALLOWED_ORIGINS`
- 检查 `VITE_API_BASE_URL` 是否指向正确的后端地址

### Q3：图片上传成功但无法预览

- 检查 MinIO Bucket 的 Public Policy 是否设置为 Read Only
- 检查 `MINIO_PUBLIC_BASE_URL` 能否从浏览器直接访问

### Q4：API 请求跨域被拒

在后端 `.env.docker` 中设置：
```
CORS_ALLOWED_ORIGINS=http://your-domain.com,http://127.0.0.1:7821
```
然后重建：`docker compose up -d --build`

---

## 八、生产安全建议

1. **更换默认密码**：MySQL/Redis/MinIO 的密码不要用示例值
2. **JWT_SECRET_KEY**：每次部署必须换成随机长字符串
3. **防火墙白名单**：仅开放 80/443 端口，关闭 3306/6379/9000 的公网访问
4. **HTTPS**：用 Let's Encrypt 免费证书 + Certbot：
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```
5. **定期备份**：MySQL dump + MinIO 数据同步到远端 OSS/S3
