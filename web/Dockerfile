# ---------- 阶段 1：构建 ----------
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci

COPY . .
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

# ---------- 阶段 2：Nginx 运行 ----------
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
