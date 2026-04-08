# Qcode 开发环境

## 快速启动

```bash
# 一键启动前后端服务
./start.sh

# 运行健康检查
./test.sh
```

## 手动启动

### 前端
```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

### 后端
```bash
cd backend_server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
# 访问 http://localhost:8000
```

## 项目结构

```
Qcode/
├── frontend/           # React 18 + TypeScript + Vite 5
│   ├── src/
│   │   ├── components/  # UI组件
│   │   ├── stores/      # Zustand状态管理
│   │   ├── services/    # API服务
│   │   └── types/       # TypeScript类型
│   └── package.json
├── backend_server/      # FastAPI后端
│   ├── main.py         # API入口
│   ├── requirements.txt
│   └── venv/           # Python虚拟环境
├── start.sh            # 一键启动脚本
└── test.sh             # 健康检查脚本
```

## 技术栈

- **前端**: React 18, TypeScript, Vite 5, Tailwind CSS, Zustand
- **后端**: FastAPI, Uvicorn, SQLAlchemy, Pydantic
- **通信**: REST API + SSE (计划WebSocket)

## 故障排除

如果端口被占用:
```bash
lsof -ti:5173 | xargs kill -9  # 清理前端端口
lsof -ti:8000 | xargs kill -9  # 清理后端端口
```
