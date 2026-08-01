# 阶段 1 : 构建 Vue 静态文件
# node:22-alpine（Node 20 已于 2026-04 停止维护）
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# npm ci：按 lockfile 精确安装，构建可复现（比 npm install 严格）
RUN npm ci
COPY . .

# 关键: 构建时注入 API 地址（同源 /api，由 Nginx 代理到后端）
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# 阶段 2 : Nginx 服务静态文件
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

