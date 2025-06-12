"""Data models for AI development sessions and interactions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class AIInteraction:
    """Represents a single AI interaction (request/response cycle)."""
    
    interaction_id: str
    session_id: str
    timestamp: datetime
    request_tokens: int = 0
    response_tokens: int = 0
    total_tokens: int = 0
    model_name: Optional[str] = None
    prompt_type: Optional[str] = None
    response_time_ms: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate total tokens if not provided."""
        if self.total_tokens == 0:
            self.total_tokens = self.request_tokens + self.response_tokens


@dataclass
class DevelopmentSession:
    """Represents a development session with AI assistance."""
    
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    total_interactions: int = 0
    total_tokens: int = 0
    total_request_tokens: int = 0
    total_response_tokens: int = 0
    project_path: Optional[str] = None
    user_id: Optional[str] = None
    claude_version: Optional[str] = None
    interactions: List[AIInteraction] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def add_interaction(self, interaction: AIInteraction):
        """Add an AI interaction to this session."""
        self.interactions.append(interaction)
        self.total_interactions += 1
        self.total_tokens += interaction.total_tokens
        self.total_request_tokens += interaction.request_tokens
        self.total_response_tokens += interaction.response_tokens
    
    def end_session(self, end_time: Optional[datetime] = None):
        """Mark the session as ended."""
        self.end_time = end_time or datetime.utcnow()
        if self.start_time and self.end_time:
            self.total_duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    @property
    def is_active(self) -> bool:
        """Check if the session is still active."""
        return self.end_time is None
    
    @property
    def average_tokens_per_interaction(self) -> float:
        """Calculate average tokens per interaction."""
        if self.total_interactions == 0:
            return 0.0
        return self.total_tokens / self.total_interactions


@dataclass
class TelemetryEvent:
    """Represents a raw telemetry event from OpenTelemetry."""
    
    event_id: str
    event_type: str  # 'metric' or 'trace'
    timestamp: datetime
    session_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    processed: bool = False
    
    @classmethod
    def from_metric(cls, metric_data: Dict[str, Any]) -> 'TelemetryEvent':
        """Create a TelemetryEvent from processed metric data."""
        return cls(
            event_id=f"metric_{datetime.utcnow().timestamp()}",
            event_type='metric',
            timestamp=datetime.fromisoformat(metric_data.get('timestamp', datetime.utcnow().isoformat())),
            session_id=metric_data.get('resource_attributes', {}).get('session.id'),
            data=metric_data
        )
    
    @classmethod
    def from_trace(cls, trace_data: Dict[str, Any]) -> 'TelemetryEvent':
        """Create a TelemetryEvent from processed trace data."""
        return cls(
            event_id=f"trace_{trace_data.get('span_id', datetime.utcnow().timestamp())}",
            event_type='trace',
            timestamp=datetime.fromisoformat(trace_data.get('start_time', datetime.utcnow().isoformat())),
            session_id=trace_data.get('resource_attributes', {}).get('session.id'),
            data=trace_data
        )
    
    @classmethod
    def from_log(cls, log_data: Dict[str, Any]) -> 'TelemetryEvent':
        """Create a TelemetryEvent from processed log data."""
        return cls(
            event_id=f"log_{datetime.utcnow().timestamp()}",
            event_type='log',
            timestamp=datetime.fromisoformat(log_data.get('timestamp', datetime.utcnow().isoformat())),
            session_id=log_data.get('resource_attributes', {}).get('session.id'),
            data=log_data
        )


@dataclass
class SessionSummary:
    """Summary statistics for a development session."""
    
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[float]
    total_interactions: int
    total_tokens: int
    average_tokens_per_interaction: float
    models_used: List[str]
    project_path: Optional[str]
    
    @classmethod
    def from_session(cls, session: DevelopmentSession) -> 'SessionSummary':
        """Create a summary from a DevelopmentSession."""
        duration_minutes = None
        if session.total_duration_ms:
            duration_minutes = session.total_duration_ms / (1000 * 60)
        
        models_used = list(set(
            interaction.model_name 
            for interaction in session.interactions 
            if interaction.model_name
        ))
        
        return cls(
            session_id=session.session_id,
            start_time=session.start_time,
            end_time=session.end_time,
            duration_minutes=duration_minutes,
            total_interactions=session.total_interactions,
            total_tokens=session.total_tokens,
            average_tokens_per_interaction=session.average_tokens_per_interaction,
            models_used=models_used,
            project_path=session.project_path
        )