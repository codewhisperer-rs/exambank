#!/bin/bash

# 确保所有必要的路径都添加到 PATH
export PATH="/usr/local/bin:/usr/local/lib/node_modules/bin:/usr/local/lib/nodejs/node-v19.9.0/bin:$PATH"

# 检查命令可用性
echo "检查命令可用性..."
echo "Node: $(node -v 2>/dev/null || echo '未找到')"
echo "npm: $(npm -v 2>/dev/null || echo '未找到')"
echo "pnpm: $(pnpm -v 2>/dev/null || echo '未找到')"

# 显示 pnpm 可能的位置
echo "查找 pnpm 位置..."
find /usr -name "pnpm*" 2>/dev/null || echo "找不到 pnpm 文件"
echo "PATH=$PATH"

# 检查代理设置
echo "检查代理设置..."
echo "HTTP_PROXY: $HTTP_PROXY"
echo "HTTPS_PROXY: $HTTPS_PROXY"

# 尝试通过代理连接外部网络
echo "测试代理连接..."
if [ -n "$HTTP_PROXY" ]; then
  curl -s --connect-timeout 5 -x $HTTP_PROXY https://www.google.com > /dev/null
  if [ $? -eq 0 ]; then
    echo "代理连接成功！"
  else
    echo "警告: 代理连接测试失败，但将继续启动服务。"
  fi
else
  echo "未设置代理，跳过代理测试。"
fi

# 启动AI助教服务（后台运行）
cd /app/aqua-ai-chat-teacher-assistant
echo "尝试启动 AI 助教服务..."

# 尝试使用不同方法启动，并确保使用固定端口3000
if command -v pnpm &> /dev/null; then
  echo "使用 pnpm 启动在端口3000..."
  PORT=3000 pnpm start &
elif command -v npm &> /dev/null; then
  echo "使用 npm 启动在端口3000（pnpm 不可用）..."
  PORT=3000 npm start &
elif [ -f "node_modules/.bin/next" ]; then
  echo "使用 next 直接启动在端口3000（npm 和 pnpm 不可用）..."
  PORT=3000 ./node_modules/.bin/next start -p 3000 &
else
  echo "错误: 无法找到 pnpm, npm 或 next。无法启动 AI 助教服务。"
  exit 1
fi

# 等待AI助教服务启动
echo "等待AI助教服务在端口3000上启动..."
timeout=60
counter=0
while ! nc -z localhost 3000 && [ $counter -lt $timeout ]; do
  sleep 1
  counter=$((counter+1))
  echo "等待AI助教服务启动... $counter/$timeout"
done

if [ $counter -eq $timeout ]; then
  echo "AI助教服务启动超时！"
  exit 1
fi

echo "AI助教服务已成功启动！"

# 启动ExamBank服务
echo "启动题库系统服务..."
cd /app/exambank

# 输出当前目录内容，确认文件存在
echo "当前ExamBank目录内容:"
ls -la

# 检查manage.py是否存在
if [ ! -f "manage.py" ]; then
    echo "错误: manage.py文件不存在!"
    exit 1
fi

# 检查数据库文件
if [ -f "db.sqlite3" ]; then
    echo "数据库文件存在: db.sqlite3"
else
    echo "警告: 数据库文件不存在，将创建新数据库"
fi

# 设置日志级别
export DJANGO_LOG_LEVEL=INFO

# 执行数据库迁移
echo "执行数据库迁移..."
python manage.py migrate --verbosity 2

echo "收集静态文件..."
python manage.py collectstatic --noinput --verbosity 2

# 设置Django环境变量
export DJANGO_SETTINGS_MODULE=exambank.settings
echo "Django设置模块: $DJANGO_SETTINGS_MODULE"

# 启动Django应用 - 使用gunicorn或daphne如果可用
echo "正在启动Django服务，端口8002..."
echo "使用Django开发服务器启动..."
python manage.py runserver 0.0.0.0:8002 --verbosity 2 &
WEB_PID=$!

# 等待Django服务启动
echo "等待Django服务启动..."
timeout=60
counter=0
while [ $counter -lt $timeout ]; do
  sleep 3
  counter=$((counter+3))
  echo "等待题库服务启动... $counter/$timeout"
  
  # 使用curl检查服务
  if curl -s -I http://localhost:8002/ 2>&1 | grep -q "HTTP/"; then
    echo "题库系统服务已成功启动！"
    break
  fi
  
  # 检查进程是否还在运行
  if ! kill -0 $WEB_PID 2>/dev/null; then
    echo "错误: Django进程已终止，退出码: $?"
    echo "显示最后的日志:"
    tail -n 50 /app/exambank/*.log 2>/dev/null || echo "没有找到日志文件"
    break
  fi
done

if [ $counter -ge $timeout ]; then
  echo "警告: 题库服务启动检查超时，但进程仍在运行。"
  echo "尝试使用不同方法检查服务状态..."
  
  if nc -z localhost 8002; then
    echo "端口8002已被监听，服务可能已启动"
  else
    echo "端口8002未被监听"
  fi
  
  ps aux | grep python
fi

# 保持脚本运行
echo "所有服务已启动，保持容器运行..."
# 使用wait命令避免脚本退出，监控并在必要时重启
while true; do
  if ! kill -0 $WEB_PID 2>/dev/null; then
    echo "Django进程已退出，尝试重启..."
    cd /app/exambank
    python manage.py runserver 0.0.0.0:8002 --verbosity 2 &
    WEB_PID=$!
  fi
  sleep 10
done 