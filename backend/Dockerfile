FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖(bcrypt 编译需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 的缓存机制，减少构建时间
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# 复制代码
COPY app ./app
COPY scripts ./scripts
COPY entrypoint.sh ./entrypoint.sh

# 确保入口脚本有可执行权限（Windows 提交可能丢失 +x 位）
RUN chmod +x ./entrypoint.sh

# 输出端口
EXPOSE 8000

# 启动命令
CMD ["./entrypoint.sh"]

