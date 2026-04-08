from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Qcode Backend API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "qcode-backend", "version": "0.2.0"}

@app.get("/")
async def root():
    return {"message": "Qcode Backend API is running", "version": "0.2.0", "docs": "/docs"}

@app.post("/api/chat")
async def chat_endpoint(payload: dict):
    return {"response": "后端服务已启动（简化版）", "status": "success"}

@app.get("/api/tasks")
async def get_tasks():
    return []

@app.post("/api/tasks")
async def create_task(task: dict):
    return {"id": 1, "subject": task.get("subject"), "status": "pending"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
