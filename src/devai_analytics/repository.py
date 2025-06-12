"""Repository layer for database operations."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from .database import SessionModel, InteractionModel, TelemetryEventModel, get_db_session
from .models import DevelopmentSession, AIInteraction, TelemetryEvent


class SessionRepository:
    """Repository for session operations."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_db_session()
    
    def create_session(self, session: DevelopmentSession) -> SessionModel:
        """Create a new session in the database."""
        db_session = SessionModel(
            session_id=session.session_id,
            start_time=session.start_time,
            end_time=session.end_time,
            total_duration_ms=session.total_duration_ms,
            total_interactions=session.total_interactions,
            total_tokens=session.total_tokens,
            total_request_tokens=session.total_request_tokens,
            total_response_tokens=session.total_response_tokens,
            project_path=session.project_path,
            user_id=session.user_id,
            claude_version=session.claude_version,
            attributes=session.attributes
        )
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        return db_session
    
    def get_session(self, session_id: str) -> Optional[SessionModel]:
        """Get a session by ID."""
        return self.db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    
    def update_session(self, session_id: str, **kwargs) -> Optional[SessionModel]:
        """Update a session with new values."""
        db_session = self.get_session(session_id)
        if not db_session:
            return None
        
        for key, value in kwargs.items():
            if hasattr(db_session, key):
                setattr(db_session, key, value)
        
        db_session.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_session)
        return db_session
    
    def list_sessions(self, limit: int = 100, offset: int = 0) -> List[SessionModel]:
        """List sessions with pagination."""
        return (self.db.query(SessionModel)
                .order_by(desc(SessionModel.start_time))
                .offset(offset)
                .limit(limit)
                .all())
    
    def get_active_sessions(self) -> List[SessionModel]:
        """Get all active (not ended) sessions."""
        return self.db.query(SessionModel).filter(SessionModel.end_time.is_(None)).all()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its interactions."""
        db_session = self.get_session(session_id)
        if not db_session:
            return False
        
        self.db.delete(db_session)
        self.db.commit()
        return True


class InteractionRepository:
    """Repository for interaction operations."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_db_session()
    
    def create_interaction(self, interaction: AIInteraction) -> InteractionModel:
        """Create a new interaction in the database."""
        db_interaction = InteractionModel(
            interaction_id=interaction.interaction_id,
            session_id=interaction.session_id,
            timestamp=interaction.timestamp,
            request_tokens=interaction.request_tokens,
            response_tokens=interaction.response_tokens,
            total_tokens=interaction.total_tokens,
            model_name=interaction.model_name,
            prompt_type=interaction.prompt_type,
            response_time_ms=interaction.response_time_ms,
            attributes=interaction.attributes
        )
        self.db.add(db_interaction)
        self.db.commit()
        self.db.refresh(db_interaction)
        return db_interaction
    
    def get_interaction(self, interaction_id: str) -> Optional[InteractionModel]:
        """Get an interaction by ID."""
        return self.db.query(InteractionModel).filter(InteractionModel.interaction_id == interaction_id).first()
    
    def get_session_interactions(self, session_id: str) -> List[InteractionModel]:
        """Get all interactions for a session."""
        return (self.db.query(InteractionModel)
                .filter(InteractionModel.session_id == session_id)
                .order_by(InteractionModel.timestamp)
                .all())
    
    def list_interactions(self, limit: int = 100, offset: int = 0) -> List[InteractionModel]:
        """List interactions with pagination."""
        return (self.db.query(InteractionModel)
                .order_by(desc(InteractionModel.timestamp))
                .offset(offset)
                .limit(limit)
                .all())
    
    def get_interactions_by_model(self, model_name: str) -> List[InteractionModel]:
        """Get interactions for a specific model."""
        return (self.db.query(InteractionModel)
                .filter(InteractionModel.model_name == model_name)
                .order_by(desc(InteractionModel.timestamp))
                .all())


class TelemetryRepository:
    """Repository for telemetry event operations."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_db_session()
    
    def create_event(self, event: TelemetryEvent) -> TelemetryEventModel:
        """Create a new telemetry event in the database."""
        db_event = TelemetryEventModel(
            event_id=event.event_id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            session_id=event.session_id,
            data=event.data,
            processed=event.processed
        )
        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)
        return db_event
    
    def get_unprocessed_events(self) -> List[TelemetryEventModel]:
        """Get all unprocessed telemetry events."""
        return self.db.query(TelemetryEventModel).filter(TelemetryEventModel.processed == False).all()
    
    def mark_processed(self, event_id: str) -> bool:
        """Mark a telemetry event as processed."""
        db_event = self.db.query(TelemetryEventModel).filter(TelemetryEventModel.event_id == event_id).first()
        if not db_event:
            return False
        
        db_event.processed = True
        self.db.commit()
        return True
    
    def get_session_events(self, session_id: str) -> List[TelemetryEventModel]:
        """Get telemetry events for a specific session."""
        return (self.db.query(TelemetryEventModel)
                .filter(TelemetryEventModel.session_id == session_id)
                .order_by(TelemetryEventModel.timestamp)
                .all())


def close_db_session():
    """Close the current database session."""
    try:
        db = get_db_session()
        db.close()
    except Exception:
        pass