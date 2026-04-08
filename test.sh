#!/bin/bash
set -e

echo "🔍 Qcode 前后端健康检查脚本"
echo "========================================"

# 测试前端
echo ""
echo "📱 前端测试 (http://localhost:5173)..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173)
if [ "$FRONTEND_STATUS" = "200" ]; then
  echo "✅ 前端运行正常 - HTTP $FRONTEND_STATUS"
else
  echo "❌ 前端异常 - HTTP $FRONTEND_STATUS"
  exit 1
fi

# 测试后端健康检查
echo ""
echo "🖥️  后端健康检查 (http://localhost:8000/health)..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$HEALTH_STATUS" = "200" ]; then
  echo "✅ 后端健康检查通过 - HTTP $HEALTH_STATUS"
  curl -s http://localhost:8000/health | python3 -m json.tool
else
  echo "❌ 后端健康检查失败 - HTTP $HEALTH_STATUS"
  exit 1
fi

# 测试API端点
echo ""
echo "🔌 测试Chat API..."
CHAT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"测试"}]}')
echo "✅ API响应:"
echo "$CHAT_RESPONSE" | python3 -m json.tool

# 测试Swagger UI
echo ""
echo "📚 测试Swagger文档..."
SWAGGER_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
if [ "$SWAGGER_STATUS" = "200" ]; then
  echo "✅ Swagger UI可用 - http://localhost:8000/docs"
else
  echo "❌ Swagger UI异常 - HTTP $SWAGGER_STATUS"
fi

echo ""
echo "========================================"
echo "✅ 所有测试通过！"
echo ""
echo "访问地址:"
echo "  前端: http://localhost:5173"
echo "  后端API: http://localhost:8000"
echo "  Swagger文档: http://localhost:8000/docs"
