from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum
import datetime

Base = declarative_base()

class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class TaskPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TeammateStatus(enum.Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    IDLE = "idle"

class ProtocolStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(200), nullable=False)
    title = Column(String(200))
    description = Column(Text)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    assignee = Column(String(50))
    owner = Column(String(50))
    requiredRole = Column(String(50))
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    blockedBy = Column(JSON, default=list)
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Teammate(Base):
    __tablename__ = "teammates"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    role = Column(String(50))
    status = Column(SQLEnum(TeammateStatus), default=TeammateStatus.OFFLINE)
    avatar = Column(String(255))
    lastSeen = Column(DateTime, server_default=func.now())

class Protocol(Base):
    __tablename__ = "protocols"
    
    id = Column(String(50), primary_key=True)
    kind = Column(String(50), nullable=False)  # 'shutdown' or 'plan_approval'
    status = Column(SQLEnum(ProtocolStatus), default=ProtocolStatus.PENDING)
    teammate = Column(String(50))
    reason = Column(Text)
    reason: str
    createdAt = Column(DateTime, server_default=func.now())
    updatedAt = Column(DateTime, server_default=func.now(), onupdate=func.now())
