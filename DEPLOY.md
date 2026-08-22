# PhotoStyle 生产部署指南（域名 + HTTPS）

## 架构概览

```
用户浏览器
    │  https://app.yourdomain.com (443)
    ▼
┌──────────────────┐
│ 宿主机 Nginx      │  ← SSL 终止 + Let's Encrypt 证书
│ (反向代理 443→端口)│
└────────┬─────────┘
         │  HTTP
         ├── /          → 127.0.0.1:7821 (前端)
         └── /api/      → 127.0.0.1:7823 (后端)
         │                    │
         ▼                    ▼
  ┌──────────────┐     ┌──────────────┐
  │ web 容器      │     │ backend 容器  │
  │ Nginx :7821  │     │ Uvicorn:7823 │
  │ (Vue 静态文件) │     │ (FastAPI)    │
  └──────────────┘     └──────────────┘
         │                    │
         ▼                    ▼
    MySQL / Redis / MinIO（宿主机或全量容器化）
```

> 用户访问 `https://app.yourdomain.com` 无需带端口号，宿主机 Nginx 自动将请求分发到对应容器。

## 环境要求

- **服务器**：Linux (Ubuntu 20.04+ / CentOS 7+) 建议 2C4G 以上
- **Docker**：20.10+ & Docker Compose v2.x
- **域名**：已备案域名（国内服务器必须备案）
- **DNS**：域名 A 记录指向服务器公网 IP

---

## 一、服务器环境准备

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

### 1.2 安装宿主机 Nginx（用于 HTTPS 终止）

**Ubuntu/Debian：**
```bash
sudo apt update
sudo apt install -y nginx
sudo systemctl enable --now nginx
```

**CentOS/RHEL：**
```bash
sudo yum install -y epel-release
sudo yum install -y nginx
sudo systemctl enable --now nginx
```

### 1.3 安装宿主机 MySQL / Redis / MinIO

如果服务器还没有这些服务，快速拉起：

```bash
# MySQL 8.0
docker run -d --name photostyle-mysql \
  -e MYSQL_ROOT_PASSWORD=你的强密码 \
  -e MYSQL_DATABASE=photostyle \
  -p 127.0.0.1:3306:3306 \
  -v mysql_data:/var/lib/mysql \
  mysql:8.0

# Redis 7
docker run -d --name photostyle-redis \
  -p 127.0.0.1:6379:6379 \
  redis:7-alpine --requirepass 你的Redis密码

# MinIO
docker run -d --name photostyle-minio \
  -p 127.0.0.1:9000:9000 -p 127.0.0.1:9001:9001 \
  -e MINIO_ROOT_USER=你的AccessKey \
  -e MINIO_ROOT_PASSWORD=你的SecretKey \
  -v minio_data:/data \
  minio/minio server /data --console-address ":9001"
```

> **安全提示**：注意端口绑定 `127.0.0.1`，只允许本地访问，不暴露到公网。

---

## 二、域名与 DNS 配置

### 2.1 添加 DNS 解析

在域名服务商控制台添加 A 记录：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---------|---------|--------|-----|
| A | app | 你的服务器公网IP | 600 |

> 将 `app` 替换为你实际想用的二级域名前缀，如 `photo`、`img` 等。

### 2.2 验证 DNS 生效

```bash
# 等待几分钟后，在服务器或本地执行：
ping app.yourdomain.com
# 应返回你的服务器 IP
```

### 2.3 国内服务器备案

如果使用国内云服务器（阿里云、腾讯云等），必须完成 ICP 备案后才能使用 80/443 端口。备案流程参考各云服务商文档。

---

## 三、部署应用

### 3.1 上传代码到服务器

```bash
# 方式 1：Git 拉取（推荐）
cd /opt
git clone https://gitee.com/你的仓库/PhotoStyle.git
cd PhotoStyle

# 方式 2：scp 上传
scp -r ./PhotoStyle root@your-server-ip:/opt/PhotoStyle
```

### 3.2 配置环境变量

```bash
cd /opt/PhotoStyle
cp .env.docker.example .env.docker
```

编辑 `.env.docker`，修改以下关键配置：

```bash
vim .env.docker   # 或 nano .env.docker
```

**必须修改的配置项：**

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `DATABASE_URL` | MySQL 连接串 | `mysql+aiomysql://root:密码@host.docker.internal:3306/photostyle` |
| `REDIS_URL` | Redis 连接串 | `redis://:密码@host.docker.internal:6379/0` |
| `DASHSCOPE_API_KEY` | 千问 API Key | `sk-xxxxxxxxxxxxx` |
| `MINIO_ENDPOINT` | MinIO 地址 | `127.0.0.1:9000` 或域名 |
| `MINIO_PUBLIC_BASE_URL` | 文件访问 URL | `https://你的域名/minio` 或 MinIO 域名 |
| `MINIO_ACCESS_KEY` | MinIO 用户名 | 实际值 |
| `MINIO_SECRET_KEY` | MinIO 密码 | 实际值 |
| `JWT_SECRET_KEY` | JWT 密钥 | 随机长字符串 |
| `CORS_ALLOWED_ORIGINS` | 允许的域名 | `https://app.yourdomain.com` |
| `SMTP_HOST/USERNAME/PASSWORD` | 邮件服务 | 实际 SMTP 配置 |

**生成随机 JWT 密钥：**
```bash
openssl rand -hex 32
```

### 3.3 构建并启动

```bash
docker compose up -d --build
```

### 3.4 验证容器运行状态

```bash
docker compose ps
```

预期输出：
```
NAME                    STATUS       PORTS
photostyle-backend      Up           0.0.0.0:7823->7823/tcp
photostyle-web          Up           0.0.0.0:7821->80/tcp
```

### 3.5 端口访问测试

```bash
# 后端
curl http://127.0.0.1:7823/api/v1/health

# 前端
curl http://127.0.0.1:7821
```

---

## 四、配置 HTTPS（Let's Encrypt + Nginx）

### 4.1 安装 Certbot

**Ubuntu/Debian：**
```bash
sudo apt install -y certbot python3-certbot-nginx
```

**CentOS/RHEL：**
```bash
sudo yum install -y epel-release
sudo yum install -y certbot python3-certbot-nginx
```

### 4.2 创建 Nginx 站点配置

```bash
sudo vim /etc/nginx/conf.d/photostyle.conf
```

写入以下内容（**替换 `app.yourdomain.com`** 为你的实际二级域名）：

```nginx
server {
    listen 80;
    server_name app.yourdomain.com;

    # ---------- 前端 ----------
    location / {
        proxy_pass http://127.0.0.1:7821;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ---------- 后端 API + WebSocket ----------
    location /api/ {
        proxy_pass http://127.0.0.1:7823/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持（IP 贴纸聊天）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # AI 生成超时
        client_max_body_size 20M;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

### 4.3 测试 Nginx 配置并重载

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 4.4 申请 SSL 证书

```bash
sudo certbot --nginx -d app.yourdomain.com
```

按提示操作：
- 输入邮箱（证书到期提醒）
- 同意服务协议
- 选择是否将 HTTP 自动重定向到 HTTPS（**建议选 2 - Redirect**）

Certbot 会自动：
1. 申请并安装 Let's Encrypt 证书
2. 修改 Nginx 配置添加 SSL 相关指令
3. 设置 HTTP → HTTPS 自动重定向

### 4.5 验证 HTTPS

```bash
# 检查证书
curl -vI https://app.yourdomain.com 2>&1 | grep -E 'subject|issuer|expire'
```

浏览器访问 `https://app.yourdomain.com`，确认地址栏显示锁图标。

### 4.6 证书自动续期

Certbot 安装后会自动设置 cron / systemd timer，证书到期前自动续期。验证：

```bash
sudo certbot renew --dry-run
```

---

## 五、防火墙与安全

### 5.1 开放必要端口

```bash
# Ubuntu (ufw)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable

# CentOS (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

### 5.2 关闭不必要的公网端口

确保以下端口**不暴露到公网**（只绑定 127.0.0.1）：
- MySQL: 3306
- Redis: 6379
- MinIO API: 9000
- 后端 API: 7823
- 前端容器: 7821

在云服务器安全组中也应关闭这些端口。

### 5.3 生产安全检查清单

- [ ] 修改所有默认密码（MySQL/Redis/MinIO）
- [ ] JWT_SECRET_KEY 使用随机长字符串
- [ ] CORS_ALLOWED_ORIGINS 只填允许的域名
- [ ] SMTP/支付宝配置填入真实值
- [ ] 防火墙只开放 22/80/443
- [ ] HTTPS 正常工作，HTTP 自动重定向

---

## 六、MinIO 对象存储配置

### 6.1 设置 Bucket 公开读取

图片需要用户通过 URL 直接访问，因此 Bucket 需要设置为公开读取：

```bash
# 安装 mc（MinIO Client）
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# 配置 MinIO 连接
mc alias set myminio http://127.0.0.1:9000 你的AccessKey 你的SecretKey

# 设置 Bucket 策略为只读
mc policy set download myminio/photostyle
```

### 6.2 MinIO 使用 CDN 域名（可选）

如果想让图片 URL 也走 HTTPS 域名，可以给 MinIO 配一个子域名（如 `cdn.yourdomain.com`）：

1. DNS 添加 `cdn` A 记录指向服务器 IP
2. 用 Certbot 申请证书：`sudo certbot --nginx -d cdn.yourdomain.com`
3. Nginx 添加 MinIO 反代配置：

```nginx
server {
    listen 443 ssl;
    server_name cdn.yourdomain.com;
    # Certbot 生成的 SSL 配置...

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. 修改 `.env.docker`：
```
MINIO_PUBLIC_BASE_URL=https://cdn.yourdomain.com
```

---

## 七、日常运维

| 操作 | 命令 |
|------|------|
| 重启所有服务 | `docker compose restart` |
| 只重启后端 | `docker compose restart backend` |
| 更新代码后重新构建 | `git pull && docker compose up -d --build` |
| 查看后端日志 | `docker compose logs -f backend` |
| 查看前端日志 | `docker compose logs -f web` |
| 进入后端容器 | `docker exec -it photostyle-backend bash` |
| 查看磁盘占用 | `docker system df` |
| 清理无用镜像 | `docker system prune -af` |
| 停止所有服务 | `docker compose down` |
| 查看 SSL 证书到期 | `sudo certbot certificates` |
| 手动续期证书 | `sudo certbot renew` |

---

## 八、常见问题

### Q1：HTTPS 访问后 API 请求报 Mixed Content

前端在 HTTPS 页面中请求了 HTTP 接口。确认：
- `.env.docker` 中 `CORS_ALLOWED_ORIGINS` 包含 `https://app.yourdomain.com`
- 前端 `VITE_API_BASE_URL` 使用相对路径 `/api/v1`（Docker 构建时已设置）

### Q2：WebSocket 连接失败

检查宿主机 Nginx 的 `/api/` location 中是否包含：
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### Q3：图片上传成功但无法预览

- 检查 MinIO Bucket 策略是否为 `download`（公开读取）
- 检查 `MINIO_PUBLIC_BASE_URL` 是否可从浏览器直接访问
- 如果 MinIO 走了 CDN 域名，确认该域名 HTTPS 证书正常

### Q4：后端连接数据库失败

容器通过 `host.docker.internal` 访问宿主机服务。部分 Linux 系统需要额外配置：

```yaml
# docker-compose.yml 中 backend 服务已有：
extra_hosts:
  - "host.docker.internal:host-gateway"
```

如果仍有问题，可改为使用宿主机内网 IP（如 `172.17.0.1`）。

### Q5：Certbot 申请证书失败

- 确认域名 DNS 已解析到本服务器
- 确认 80 端口对外开放且 Nginx 正在运行
- 确认域名已完成备案（国内服务器）

---

## 九、完整部署流程速查

```bash
# 1. 服务器装好 Docker + Nginx + MySQL/Redis/MinIO
# 2. 域名 DNS 解析到服务器
# 3. 上传代码
git clone https://gitee.com/xxx/PhotoStyle.git /opt/PhotoStyle
cd /opt/PhotoStyle

# 4. 配置环境变量
cp .env.docker.example .env.docker
vim .env.docker

# 5. 构建启动
docker compose up -d --build

# 6. 验证本地可用
curl http://127.0.0.1:7821
curl http://127.0.0.1:7823/docs

# 7. 配置 Nginx 反代
sudo vim /etc/nginx/conf.d/photostyle.conf
# 写入反代配置（见第四节）
sudo nginx -t && sudo systemctl reload nginx

# 8. 申请 HTTPS 证书
sudo certbot --nginx -d app.yourdomain.com

# 9. 验证
# 浏览器打开 https://app.yourdomain.com

# 10. 安全检查
# - 防火墙只开 22/80/443
# - 确认数据库等端口不暴露公网
```
