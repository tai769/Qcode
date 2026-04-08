from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Enum as SQLEnum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class TaskPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

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
    
    def to_dict(self):
        return {
            "id": self.id,
            "subject": self.subject,
            "title": self.title,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "assignee": self.assignee,
            "owner": self.owner,
            "requiredRole": self.requiredRole,
            "priority": self.priority.value if self.priority else None,
            "blockedBy": self.blockedBy or [],
            "createdAt": self.createdAt.isoformat() if self.createdAt else None,
            "updatedAt": self.updatedAt.isoformat() if self.updatedAt else None
        }

# SQLite内存数据库
engine = create_engine("sqlite:///./qcode.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
