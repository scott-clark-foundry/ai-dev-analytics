"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class SessionBase(BaseModel):
    """Base schema for sessions."""
    session_id: str = Field(..., description="Unique session identifier")
    project_path: Optional[str] = Field(None, description="Project directory path")
    user_id: Optional[str] = Field(None, description="User identifier")
    claude_version: Optional[str] = Field(None, description="Claude version used")
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional session attributes")


class SessionCreate(SessionBase):
    """Schema for creating a new session."""
    start_time: datetime = Field(..., description="Session start timestamp")


class SessionUpdate(BaseModel):
    """Schema for updating a session."""
    end_time: Optional[datetime] = Field(None, description="Session end timestamp")
    total_duration_ms: Optional[float] = Field(None, description="Total session duration in milliseconds")
    total_interactions: Optional[int] = Field(None, description="Total number of interactions")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    total_request_tokens: Optional[int] = Field(None, description="Total request tokens")
    total_response_tokens: Optional[int] = Field(None, description="Total response tokens")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Additional session attributes")


class SessionResponse(SessionBase):
    """Schema for session API responses."""
    id: int = Field(..., description="Database ID")
    start_time: datetime = Field(..., description="Session start timestamp")
    end_time: Optional[datetime] = Field(None, description="Session end timestamp")
    total_duration_ms: Optional[float] = Field(None, description="Total session duration in milliseconds")
    total_interactions: int = Field(0, description="Total number of interactions")
    total_tokens: int = Field(0, description="Total tokens used")
    total_request_tokens: int = Field(0, description="Total request tokens")
    total_response_tokens: int = Field(0, description="Total response tokens")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")
    
    class Config:
        from_attributes = True


class InteractionBase(BaseModel):
    """Base schema for interactions."""
    interaction_id: str = Field(..., description="Unique interaction identifier")
    session_id: str = Field(..., description="Associated session ID")
    timestamp: datetime = Field(..., description="Interaction timestamp")
    request_tokens: int = Field(0, description="Request tokens count")
    response_tokens: int = Field(0, description="Response tokens count")
    total_tokens: int = Field(0, description="Total tokens count")
    model_name: Optional[str] = Field(None, description="AI model name")
    prompt_type: Optional[str] = Field(None, description="Type of prompt/interaction")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional interaction attributes")


class InteractionCreate(InteractionBase):
    """Schema for creating a new interaction."""
    pass


class InteractionResponse(InteractionBase):
    """Schema for interaction API responses."""
    id: int = Field(..., description="Database ID")
    created_at: datetime = Field(..., description="Record creation timestamp")
    
    class Config:
        from_attributes = True


class TelemetryEventBase(BaseModel):
    """Base schema for telemetry events."""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event type (metric, trace, log)")
    timestamp: datetime = Field(..., description="Event timestamp")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    data: Dict[str, Any] = Field(..., description="Event data payload")


class TelemetryEventCreate(TelemetryEventBase):
    """Schema for creating telemetry events."""
    pass


class TelemetryEventResponse(TelemetryEventBase):
    """Schema for telemetry event API responses."""
    id: int = Field(..., description="Database ID")
    processed: bool = Field(False, description="Whether event has been processed")
    created_at: datetime = Field(..., description="Record creation timestamp")
    
    class Config:
        from_attributes = True


class SessionSummaryResponse(BaseModel):
    """Schema for session summary with analytics."""
    session_id: str = Field(..., description="Session identifier")
    start_time: datetime = Field(..., description="Session start timestamp")
    end_time: Optional[datetime] = Field(None, description="Session end timestamp")
    duration_minutes: Optional[float] = Field(None, description="Session duration in minutes")
    total_interactions: int = Field(0, description="Total interactions count")
    total_tokens: int = Field(0, description="Total tokens used")
    average_tokens_per_interaction: float = Field(0.0, description="Average tokens per interaction")
    models_used: List[str] = Field(default_factory=list, description="List of AI models used")
    project_path: Optional[str] = Field(None, description="Project directory path")
    interaction_breakdown: Dict[str, int] = Field(default_factory=dict, description="Breakdown by interaction type")
    hourly_activity: List[Dict[str, Any]] = Field(default_factory=list, description="Hourly activity data")


class DashboardDataResponse(BaseModel):
    """Schema for dashboard analytics data."""
    total_sessions: int = Field(0, description="Total number of sessions")
    active_sessions: int = Field(0, description="Number of active sessions")
    total_interactions: int = Field(0, description="Total interactions across all sessions")
    total_tokens: int = Field(0, description="Total tokens used")
    average_session_duration: float = Field(0.0, description="Average session duration in minutes")
    models_breakdown: Dict[str, int] = Field(default_factory=dict, description="Usage by model")
    daily_activity: List[Dict[str, Any]] = Field(default_factory=list, description="Daily activity over requested period")
    top_projects: List[Dict[str, Any]] = Field(default_factory=list, description="Most active projects")


class ErrorResponse(BaseModel):
    """Schema for API error responses."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code if applicable")