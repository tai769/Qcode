from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TaskCreate(BaseModel):
    subject: str
    title: Optional[str] = None
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    requiredRole: Optional[str] = None
    blockedBy: Optional[List[int]] = []

class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    owner: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    subject: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: TaskStatus
    assignee: Optional[str] = None
    owner: Optional[str] = None
    requiredRole: Optional[str] = None
    priority: TaskPriority
    blockedBy: List[int] = []
    createdAt: str
    updatedAt: str

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    response: str
    status: str

class TeammateStatus(str, Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    IDLE = "idle"

class Teammate(BaseModel):
    id: str
    name: str
    role: str
    status: TeammateStatus
    avatar: Optional[str] = None
