"""Business logic services for analytics operations."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .database import get_db_session, SessionModel, InteractionModel, TelemetryEventModel
from .repository import SessionRepository, InteractionRepository, TelemetryRepository
from .schemas import (
    SessionCreate, SessionResponse, InteractionCreate, InteractionResponse,
    TelemetryEventCreate, SessionSummaryResponse, DashboardDataResponse
)
from .models import DevelopmentSession, AIInteraction, TelemetryEvent


class AnalyticsService:
    """Service for analytics operations."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_db_session()
        self.session_repo = SessionRepository(self.db)
        self.interaction_repo = InteractionRepository(self.db)
        self.telemetry_repo = TelemetryRepository(self.db)
    
    async def create_session(self, session_data: SessionCreate) -> SessionResponse:
        """Create a new development session."""
        session = DevelopmentSession(
            session_id=session_data.session_id,
            start_time=session_data.start_time,
            project_path=session_data.project_path,
            user_id=session_data.user_id,
            claude_version=session_data.claude_version,
            attributes=session_data.attributes or {}
        )
        
        db_session = self.session_repo.create_session(session)
        return SessionResponse.model_validate(db_session)
    
    async def get_session(self, session_id: str) -> Optional[SessionResponse]:
        """Get a session by ID."""
        db_session = self.session_repo.get_session(session_id)
        if not db_session:
            return None
        return SessionResponse.model_validate(db_session)
    
    async def update_session(self, session_id: str, **updates) -> Optional[SessionResponse]:
        """Update a session."""
        db_session = self.session_repo.update_session(session_id, **updates)
        if not db_session:
            return None
        return SessionResponse.model_validate(db_session)
    
    async def list_sessions(self, limit: int = 100, offset: int = 0) -> List[SessionResponse]:
        """List sessions with pagination."""
        db_sessions = self.session_repo.list_sessions(limit=limit, offset=offset)
        return [SessionResponse.model_validate(session) for session in db_sessions]
    
    async def create_interaction(self, interaction_data: InteractionCreate) -> InteractionResponse:
        """Create a new AI interaction."""
        interaction = AIInteraction(
            interaction_id=interaction_data.interaction_id,
            session_id=interaction_data.session_id,
            timestamp=interaction_data.timestamp,
            request_tokens=interaction_data.request_tokens,
            response_tokens=interaction_data.response_tokens,
            total_tokens=interaction_data.total_tokens,
            model_name=interaction_data.model_name,
            prompt_type=interaction_data.prompt_type,
            response_time_ms=interaction_data.response_time_ms,
            attributes=interaction_data.attributes or {}
        )
        
        db_interaction = self.interaction_repo.create_interaction(interaction)
        
        # Update session totals
        await self._update_session_totals(interaction_data.session_id)
        
        return InteractionResponse.model_validate(db_interaction)
    
    async def get_session_interactions(self, session_id: str) -> List[InteractionResponse]:
        """Get all interactions for a session."""
        db_interactions = self.interaction_repo.get_session_interactions(session_id)
        return [InteractionResponse.model_validate(interaction) for interaction in db_interactions]
    
    async def get_session_summary(self, session_id: str) -> Optional[SessionSummaryResponse]:
        """Get session summary with analytics."""
        db_session = self.session_repo.get_session(session_id)
        if not db_session:
            return None
        
        interactions = self.interaction_repo.get_session_interactions(session_id)
        
        # Calculate analytics
        duration_minutes = None
        if db_session.total_duration_ms:
            duration_minutes = db_session.total_duration_ms / (1000 * 60)
        
        models_used = list(set(
            interaction.model_name for interaction in interactions 
            if interaction.model_name
        ))
        
        # Interaction breakdown by type
        interaction_breakdown = {}
        for interaction in interactions:
            prompt_type = interaction.prompt_type or "unknown"
            interaction_breakdown[prompt_type] = interaction_breakdown.get(prompt_type, 0) + 1
        
        # Hourly activity
        hourly_activity = self._calculate_hourly_activity(interactions)
        
        return SessionSummaryResponse(
            session_id=db_session.session_id,
            start_time=db_session.start_time,
            end_time=db_session.end_time,
            duration_minutes=duration_minutes,
            total_interactions=db_session.total_interactions,
            total_tokens=db_session.total_tokens,
            average_tokens_per_interaction=db_session.total_tokens / max(db_session.total_interactions, 1),
            models_used=models_used,
            project_path=db_session.project_path,
            interaction_breakdown=interaction_breakdown,
            hourly_activity=hourly_activity
        )
    
    async def process_telemetry_event(self, event_data: TelemetryEventCreate):
        """Process incoming telemetry event."""
        event = TelemetryEvent(
            event_id=event_data.event_id,
            event_type=event_data.event_type,
            timestamp=event_data.timestamp,
            session_id=event_data.session_id,
            data=event_data.data
        )
        
        self.telemetry_repo.create_event(event)
        
        # Process event based on type
        if event_data.event_type == "metric":
            await self._process_metric_event(event_data)
        elif event_data.event_type == "trace":
            await self._process_trace_event(event_data)
    
    async def get_dashboard_data(self, days: int = 7) -> DashboardDataResponse:
        """Get dashboard analytics data."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Basic counts
        total_sessions = self.db.query(SessionModel).count()
        active_sessions = self.db.query(SessionModel).filter(SessionModel.end_time.is_(None)).count()
        
        recent_sessions = (self.db.query(SessionModel)
                          .filter(SessionModel.start_time >= cutoff_date)
                          .all())
        
        total_interactions = sum(session.total_interactions for session in recent_sessions)
        total_tokens = sum(session.total_tokens for session in recent_sessions)
        
        # Average session duration
        completed_sessions = [s for s in recent_sessions if s.total_duration_ms]
        avg_duration = 0.0
        if completed_sessions:
            avg_duration = sum(s.total_duration_ms for s in completed_sessions) / len(completed_sessions) / (1000 * 60)
        
        # Models breakdown
        recent_interactions = (self.db.query(InteractionModel)
                              .filter(InteractionModel.timestamp >= cutoff_date)
                              .all())
        
        models_breakdown = {}
        for interaction in recent_interactions:
            model = interaction.model_name or "unknown"
            models_breakdown[model] = models_breakdown.get(model, 0) + 1
        
        # Daily activity
        daily_activity = self._calculate_daily_activity(recent_sessions, days)
        
        # Top projects
        top_projects = self._calculate_top_projects(recent_sessions)
        
        return DashboardDataResponse(
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_interactions=total_interactions,
            total_tokens=total_tokens,
            average_session_duration=avg_duration,
            models_breakdown=models_breakdown,
            daily_activity=daily_activity,
            top_projects=top_projects
        )
    
    async def _update_session_totals(self, session_id: str):
        """Update session totals after adding interaction."""
        interactions = self.interaction_repo.get_session_interactions(session_id)
        
        total_interactions = len(interactions)
        total_tokens = sum(i.total_tokens for i in interactions)
        total_request_tokens = sum(i.request_tokens for i in interactions)
        total_response_tokens = sum(i.response_tokens for i in interactions)
        
        self.session_repo.update_session(
            session_id,
            total_interactions=total_interactions,
            total_tokens=total_tokens,
            total_request_tokens=total_request_tokens,
            total_response_tokens=total_response_tokens
        )
    
    def _calculate_hourly_activity(self, interactions: List[InteractionModel]) -> List[Dict[str, Any]]:
        """Calculate hourly activity distribution."""
        hourly_counts = {}
        for interaction in interactions:
            hour = interaction.timestamp.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        return [{"hour": hour, "count": count} for hour, count in sorted(hourly_counts.items())]
    
    def _calculate_daily_activity(self, sessions: List[SessionModel], days: int) -> List[Dict[str, Any]]:
        """Calculate daily activity over the specified period."""
        daily_counts = {}
        
        for session in sessions:
            date_key = session.start_time.date().isoformat()
            if date_key not in daily_counts:
                daily_counts[date_key] = {"sessions": 0, "interactions": 0, "tokens": 0}
            
            daily_counts[date_key]["sessions"] += 1
            daily_counts[date_key]["interactions"] += session.total_interactions
            daily_counts[date_key]["tokens"] += session.total_tokens
        
        # Ensure all days are represented
        start_date = datetime.utcnow().date() - timedelta(days=days-1)
        result = []
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_key = date.isoformat()
            data = daily_counts.get(date_key, {"sessions": 0, "interactions": 0, "tokens": 0})
            data["date"] = date_key
            result.append(data)
        
        return result
    
    def _calculate_top_projects(self, sessions: List[SessionModel]) -> List[Dict[str, Any]]:
        """Calculate top projects by activity."""
        project_stats = {}
        
        for session in sessions:
            if not session.project_path:
                continue
            
            if session.project_path not in project_stats:
                project_stats[session.project_path] = {
                    "sessions": 0,
                    "interactions": 0,
                    "tokens": 0
                }
            
            project_stats[session.project_path]["sessions"] += 1
            project_stats[session.project_path]["interactions"] += session.total_interactions
            project_stats[session.project_path]["tokens"] += session.total_tokens
        
        # Sort by total interactions and return top 10
        sorted_projects = sorted(
            project_stats.items(),
            key=lambda x: x[1]["interactions"],
            reverse=True
        )[:10]
        
        return [
            {"path": path, **stats}
            for path, stats in sorted_projects
        ]
    
    async def _process_metric_event(self, event_data: TelemetryEventCreate):
        """Process metric telemetry events."""
        # Extract metrics and create interactions if needed
        pass
    
    async def _process_trace_event(self, event_data: TelemetryEventCreate):
        """Process trace telemetry events."""
        # Extract trace data and create sessions/interactions if needed
        pass