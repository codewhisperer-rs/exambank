FROM node:19-alpine AS ai-assistant-builder

# 添加DNS配置
ENV DNS_SERVERS="8.8.8.8 8.8.4.4"

# 如果你有可用的代理，可以取消注释并配置
# ENV HTTP_PROXY=http://your-proxy-server:port
# ENV HTTPS_PROXY=http://your-proxy-server:port
# ENV NO_PROXY=localhost,127.0.0.1

WORKDIR /app/aqua-ai-chat-teacher-assistant
COPY ./aqua-ai-chat-teacher-assistant ./
RUN npm install -g pnpm
# 设置网络超时时间
RUN pnpm config set network-timeout 100000
# 设置npm注册表，使用淘宝镜像
RUN pnpm config set registry https://registry.npmmirror.com
RUN pnpm install --force
# 跳过类型检查和 linting
ENV NEXT_SKIP_TYPE_CHECK=true
ENV NEXT_SKIP_ESLINT=true
# 增加NODE_OPTIONS环境变量以增加内存限制和DNS解析顺序设置
ENV NODE_OPTIONS="--max-old-space-size=4096 --dns-result-order=ipv4first"
RUN pnpm exec next build --no-lint

FROM python:3.11-slim

# 如果你有可用的代理，可以取消注释并配置
# ENV HTTP_PROXY=http://your-proxy-server:port
# ENV HTTPS_PROXY=http://your-proxy-server:port
# ENV NO_PROXY=localhost,127.0.0.1

# 安装基本依赖
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    netcat-traditional \
    xz-utils \
    net-tools \
    procps \
    iproute2 \
    iputils-ping \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置Node.js环境变量
ENV NODE_VERSION=19.9.0

# 安装Node.js
RUN curl -fsSL https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.xz -o /tmp/node.tar.xz \
    && mkdir -p /usr/local/lib/nodejs \
    && tar -xJf /tmp/node.tar.xz -C /usr/local/lib/nodejs \
    && rm /tmp/node.tar.xz \
    && mv /usr/local/lib/nodejs/node-v$NODE_VERSION-linux-x64 /usr/local/lib/nodejs/node-v$NODE_VERSION

# 设置PATH环境变量
ENV PATH="/usr/local/lib/nodejs/node-v$NODE_VERSION/bin:$PATH"

# 验证Node.js和npm是否正确安装
RUN echo "Node.js Path: $(which node)" \
    && echo "NPM Path: $(which npm)" \
    && node -v \
    && npm -v

# 安装pnpm并验证安装
RUN npm install -g pnpm \
    && echo "Node: $(node -v)" \
    && echo "NPM: $(npm -v)" \
    && echo "PNPM: $(pnpm -v)"

WORKDIR /app

# 复制AI助教项目
COPY --from=ai-assistant-builder /app/aqua-ai-chat-teacher-assistant /app/aqua-ai-chat-teacher-assistant

# 设置ExamBank项目
COPY ./exambank/requirements.txt /app/exambank/
RUN pip install --no-cache-dir -r /app/exambank/requirements.txt
RUN pip install --no-cache-dir gunicorn django-cors-headers

RUN mkdir -p /app/exambank/db
COPY ./exambank /app/exambank/

# 复制启动脚本
COPY start.sh /app/
RUN chmod +x /app/start.sh

# 复制数据库文件
COPY ./exambank/db.sqlite3 /app/exambank/db.sqlite3

# 确保 exambank 目录有正确的权限
RUN chmod -R 755 /app/exambank

EXPOSE 3000 8002

# 启动两个应用
CMD ["/app/start.sh"] 