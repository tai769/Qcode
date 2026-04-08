from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
import api.tasks as tasks_api

app = FastAPI(title="Qcode Backend API", version="0.2.0")

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_api.router)

@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库"""
    init_db()
    print("✅ 数据库初始化完成")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "qcode-backend", "version": "0.2.0"}

@app.get("/")
async def root():
    return {
        "message": "Qcode Backend API is running",
        "version": "0.2.0",
        "docs": "/docs"
    }

@app.post("/api/chat")
async def chat_endpoint(payload: dict):
    """Demo chat endpoint"""
    return {
        "response": "这是后端演示回复。后端服务已成功启动！",
        "status": "success"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
