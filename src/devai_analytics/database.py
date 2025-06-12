"""Database models and schema for AI development analytics."""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool

Base = declarative_base()


class SessionModel(Base):
    """SQLAlchemy model for development sessions."""
    
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    total_duration_ms = Column(Float, nullable=True)
    total_interactions = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_request_tokens = Column(Integer, default=0)
    total_response_tokens = Column(Integer, default=0)
    project_path = Column(String(512), nullable=True)
    user_id = Column(String(255), nullable=True)
    claude_version = Column(String(50), nullable=True)
    attributes = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    interactions = relationship("InteractionModel", back_populates="session", cascade="all, delete-orphan")


class InteractionModel(Base):
    """SQLAlchemy model for AI interactions."""
    
    __tablename__ = 'interactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    interaction_id = Column(String(255), unique=True, nullable=False, index=True)
    session_id = Column(String(255), ForeignKey('sessions.session_id'), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    request_tokens = Column(Integer, default=0)
    response_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    model_name = Column(String(100), nullable=True)
    prompt_type = Column(String(100), nullable=True)
    response_time_ms = Column(Float, nullable=True)
    attributes = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("SessionModel", back_populates="interactions")


class TelemetryEventModel(Base):
    """SQLAlchemy model for raw telemetry events."""
    
    __tablename__ = 'telemetry_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    session_id = Column(String(255), nullable=True, index=True)
    data = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class OpenAIUsageModel(Base):
    """SQLAlchemy model for OpenAI usage data."""
    
    __tablename__ = 'openai_usage'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=True, index=True)
    date = Column(DateTime, nullable=False)
    organization_id = Column(String(255), nullable=True)
    model = Column(String(100), nullable=False)
    requests = Column(Integer, default=0)
    tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClaudeUsageModel(Base):
    """SQLAlchemy model for Claude/Anthropic usage data."""
    
    __tablename__ = 'claude_usage'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=True, index=True)
    date = Column(DateTime, nullable=False)
    organization_id = Column(String(255), nullable=True)
    model = Column(String(100), nullable=False)
    requests = Column(Integer, default=0)
    tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, database_url: str = "sqlite:///./ai_dev_analytics.db"):
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
        
    def close(self):
        """Close database connection."""
        self.engine.dispose()


_db_manager: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.create_tables()
    return _db_manager


def get_db_session() -> Session:
    """Get a database session."""
    return get_database().get_session()