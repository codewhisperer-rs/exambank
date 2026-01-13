# ExamBank与AI助教一体化Docker部署

本项目将ExamBank考试系统和AI助教项目打包在一个Docker容器中，实现一体化部署和使用。

## 文件结构

- `Dockerfile`: 容器构建文件
- `docker-compose.yml`: Docker Compose配置文件
- `start.sh`: 容器内服务启动脚本
- `exambank/`: ExamBank考试系统项目目录
- `aqua-ai-chat-teacher-assistant/`: AI助教项目目录

## 部署方法

### 前提条件

- 安装Docker和Docker Compose
- 确保端口8000和3000未被占用

### 部署步骤

1. 克隆本仓库到本地：

```bash
git clone <仓库URL>
cd app
```

2. 使用Docker Compose构建并启动服务：

```bash
docker-compose up -d
```

3. 等待服务启动完成，通常需要几分钟时间。

### 访问服务

- ExamBank考试系统: http://localhost:8000
- AI助教服务: http://localhost:3000

## 数据持久化

系统使用Docker卷进行数据持久化：

- `exambank_data`: 存储ExamBank的数据文件
- `exambank_media`: 存储上传的媒体文件
- `exambank_db`: 存储SQLite数据库文件

## 日志查看

查看容器日志：

```bash
docker-compose logs -f
```

## 停止服务

```bash
docker-compose down
```

## 常见问题排查

- 如果ExamBank无法连接到AI助教服务，请检查容器内网络是否正常。
- 如果服务启动失败，请查看日志以获取详细错误信息。 