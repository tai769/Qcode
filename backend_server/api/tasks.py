from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db, Task
from schemas import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("", response_model=List[TaskResponse])
def get_tasks(
    status: str = None,
    db: Session = Depends(get_db)
):
    """获取任务列表，支持状态过滤"""
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    tasks = query.order_by(Task.createdAt.desc()).all()
    return [task.to_dict() for task in tasks]

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取单个任务详情"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()

@router.post("", response_model=TaskResponse, status_code=201)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """创建新任务"""
    db_task = Task(
        subject=task.subject,
        title=task.title,
        description=task.description,
        priority=task.priority,
        requiredRole=task.requiredRole,
        blockedBy=task.blockedBy or []
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task.to_dict()

@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db)
):
    """更新任务（状态或owner）"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_update.status is not None:
        task.status = task_update.status
    if task_update.owner is not None:
        task.owner = task_update.owner
    
    db.commit()
    db.refresh(task)
    return task.to_dict()

@router.post("/{task_id}/claim", response_model=TaskResponse)
def claim_task(
    task_id: int,
    owner: str,
    db: Session = Depends(get_db)
):
    """认领任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.owner:
        raise HTTPException(status_code=400, detail="Task already claimed")
    
    task.owner = owner
    task.status = "in_progress"
    db.commit()
    db.refresh(task)
    return task.to_dict()

@router.post("/{task_id}/release", response_model=TaskResponse)
def release_task(task_id: int, db: Session = Depends(get_db)):
    """释放任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.owner = None
    task.status = "pending"
    db.commit()
    db.refresh(task)
    return task.to_dict()

@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}
