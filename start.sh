#!/bin/bash
set -e

echo "🚀 Qcode 开发环境启动脚本"
echo "========================================"

# 检查并启动后端
echo ""
echo "📦 检查后端环境..."
if [ ! -d "backend_server/venv" ]; then
  echo "创建后端虚拟环境..."
  cd backend_server
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt --quiet
  cd ..
fi

echo "启动后端服务 (端口8000)..."
cd backend_server
source venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info &
BACKEND_PID=$!
cd ..

sleep 3

# 检查后端是否启动成功
if curl -s -f http://localhost:8000/health > /dev/null; then
  echo "✅ 后端启动成功"
else
  echo "❌ 后端启动失败"
  exit 1
fi

# 检查并启动前端
echo ""
echo "🎨 检查前端环境..."
if [ ! -d "frontend/node_modules" ]; then
  echo "安装前端依赖..."
  cd frontend
  npm install
  cd ..
fi

echo "启动前端服务 (端口5173)..."
cd frontend
npm run dev > /tmp/qcode-frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

sleep 3

# 检查前端是否启动成功
if curl -s -f http://localhost:5173 > /dev/null; then
  echo "✅ 前端启动成功"
else
  echo "❌ 前端启动失败，查看日志:"
  cat /tmp/qcode-frontend.log
  exit 1
fi

echo ""
echo "========================================"
echo "✅ Qcode 开发环境启动成功！"
echo ""
echo "访问地址:"
echo "  前端: http://localhost:5173"
echo "  后端API: http://localhost:8000"
echo "  Swagger文档: http://localhost:8000/docs"
echo ""
echo "运行健康检查: ./test.sh"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 捕获Ctrl+C信号
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo ""; echo "🛑 服务已停止"; exit 0' INT TERM

# 保持脚本运行
wait
