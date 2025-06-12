"""FastAPI application entry point."""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from typing import List, Optional

from devai_analytics.database import get_database
from devai_analytics.schemas import (
    SessionCreate, SessionResponse, InteractionCreate, InteractionResponse,
    TelemetryEventCreate, SessionSummaryResponse
)
from devai_analytics.services import AnalyticsService
from devai_analytics.telemetry.processor import TelemetryProcessor
from devai_analytics.ai_providers import ProviderType
from devai_analytics.ai_providers.provider_manager import (
    get_provider_manager, start_all_provider_collections, stop_all_provider_collections
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Initialize database
    db = get_database()
    print("✓ Database initialized")
    
    # Start background telemetry processing
    processor = TelemetryProcessor()
    await processor.start()
    print("✓ Telemetry processor started")
    
    # Initialize and start AI provider collections
    provider_manager = get_provider_manager()
    init_results = await provider_manager.initialize()
    start_results = await start_all_provider_collections()
    
    enabled_providers = [p.value for p, success in init_results.items() if success]
    if enabled_providers:
        print(f"✓ AI providers initialized: {', '.join(enabled_providers)}")
    else:
        print("⚠ No AI providers initialized (API keys may be missing)")
    
    yield
    
    # Cleanup
    await processor.stop()
    await stop_all_provider_collections()
    db.close()
    print("✓ Application shutdown complete")


app = FastAPI(
    title="AI Development Analytics API",
    description="Track and analyze AI-assisted development sessions",
    version="0.2.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_analytics_service() -> AnalyticsService:
    """Dependency to get analytics service."""
    return AnalyticsService()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI Development Analytics API", "version": "0.2.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "database": "connected"}


# Session endpoints
@app.post("/sessions", response_model=SessionResponse)
async def create_session(
    session: SessionCreate,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Create a new development session."""
    return await service.create_session(session)


@app.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    limit: int = 100,
    offset: int = 0,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """List development sessions."""
    return await service.list_sessions(limit=limit, offset=offset)


@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Get a specific session."""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    updates: dict,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Update a session."""
    session = await service.update_session(session_id, **updates)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/sessions/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: str,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Get session summary with analytics."""
    summary = await service.get_session_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    return summary


# Interaction endpoints
@app.post("/interactions", response_model=InteractionResponse)
async def create_interaction(
    interaction: InteractionCreate,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Create a new AI interaction."""
    return await service.create_interaction(interaction)


@app.get("/sessions/{session_id}/interactions", response_model=List[InteractionResponse])
async def get_session_interactions(
    session_id: str,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Get all interactions for a session."""
    return await service.get_session_interactions(session_id)


# Telemetry endpoints
@app.post("/telemetry/ingest")
async def ingest_telemetry(
    event: TelemetryEventCreate,
    background_tasks: BackgroundTasks,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Ingest telemetry data."""
    background_tasks.add_task(service.process_telemetry_event, event)
    return {"status": "accepted"}


@app.get("/analytics/dashboard")
async def get_dashboard_data(
    days: int = 7,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Get dashboard analytics data."""
    return await service.get_dashboard_data(days=days)


@app.get("/analytics/providers")
async def get_provider_status():
    """Get status of all AI providers."""
    provider_manager = get_provider_manager()
    health_checks = await provider_manager.get_provider_health_checks()
    manager_summary = provider_manager.get_manager_summary()
    
    return {
        "manager": manager_summary,
        "providers": health_checks
    }


@app.get("/analytics/usage")
async def get_all_provider_usage(days: int = 7):
    """Get usage summary from all providers."""
    provider_manager = get_provider_manager()
    summaries = await provider_manager.get_all_usage_summaries(days=days)
    
    # Combine summaries into a unified response
    total_cost = sum(summary.total_cost for summary in summaries.values())
    total_tokens = sum(summary.total_tokens for summary in summaries.values())
    total_requests = sum(summary.total_requests for summary in summaries.values())
    
    return {
        "period_days": days,
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "total_requests": total_requests,
        "by_provider": {
            provider.value: {
                "cost": summary.total_cost,
                "tokens": summary.total_tokens,
                "requests": summary.total_requests,
                "by_model": summary.by_model,
                "daily_breakdown": summary.daily_breakdown
            }
            for provider, summary in summaries.items()
        }
    }


@app.get("/analytics/usage/{provider}")
async def get_provider_usage(provider: str, days: int = 7):
    """Get usage summary for a specific provider."""
    try:
        provider_type = ProviderType(provider.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    provider_manager = get_provider_manager()
    provider_instance = provider_manager.get_provider(provider_type)
    
    if not provider_instance:
        raise HTTPException(status_code=404, detail=f"Provider {provider} not active")
    
    summary = await provider_instance.get_usage_summary(days=days)
    return {
        "provider": provider_type.value,
        "period_days": days,
        "total_cost": summary.total_cost,
        "total_tokens": summary.total_tokens,
        "total_requests": summary.total_requests,
        "by_model": summary.by_model,
        "daily_breakdown": summary.daily_breakdown
    }


@app.post("/analytics/collect")
async def trigger_all_collections(days_back: int = 1):
    """Manually trigger usage data collection for all providers."""
    provider_manager = get_provider_manager()
    
    try:
        results = await provider_manager.collect_all_usage_data(days_back=days_back)
        
        collection_summary = {}
        total_records = 0
        
        for provider_type, records in results.items():
            record_count = len(records)
            collection_summary[provider_type.value] = {
                "success": True,
                "records_collected": record_count
            }
            total_records += record_count
        
        return {
            "status": "success",
            "message": f"Collected usage data for last {days_back} days",
            "total_records": total_records,
            "by_provider": collection_summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Collection failed: {str(e)}")


@app.post("/analytics/collect/{provider}")
async def trigger_provider_collection(provider: str, days_back: int = 1):
    """Manually trigger usage data collection for a specific provider."""
    try:
        provider_type = ProviderType(provider.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    provider_manager = get_provider_manager()
    provider_instance = provider_manager.get_provider(provider_type)
    
    if not provider_instance:
        raise HTTPException(status_code=404, detail=f"Provider {provider} not active")
    
    try:
        records = await provider_instance.collect_usage_data(days_back=days_back)
        return {
            "status": "success",
            "provider": provider_type.value,
            "message": f"Collected usage data for last {days_back} days",
            "records_collected": len(records)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Collection failed for {provider}: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )