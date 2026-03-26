# ============================================
# jz-wxbot 微信自动化 Dockerfile
# Python + GUI自动化环境
# ============================================

# ==================== 基础镜像 ====================
FROM python:3.11-windowsservercore-ltsc2022 AS base

WORKDIR /app

# 安装系统依赖
RUN pip install --upgrade pip

# ==================== 构建阶段 ====================
FROM base AS builder

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# ==================== 运行时阶段 ====================
FROM base AS runtime

# 从构建阶段复制已安装的包
COPY --from=builder C:/Python/Lib/site-packages C:/Python/Lib/site-packages

# 复制应用代码
COPY . .

# 创建日志和插件目录
RUN mkdir -p logs data plugins

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV INSTANCE_ID=wxbot-1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:9000/health')" || exit 1

# 暴露端口
EXPOSE 9000

# 启动命令
CMD ["python", "main.py"]

# ==================== 开发镜像 ====================
FROM runtime AS development

ENV LOG_LEVEL=DEBUG

CMD ["python", "-m", "pytest", "-v"]

# ==================== 标签 ====================
LABEL org.opencontainers.image.title="jz-wxbot"
LABEL org.opencontainers.image.description="WeChat Automation Bot"
LABEL org.opencontainers.image.version="2.1.0"
LABEL org.opencontainers.image.vendor="jz-wxbot Team"