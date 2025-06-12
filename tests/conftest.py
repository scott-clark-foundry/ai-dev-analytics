"""Test configuration and fixtures."""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

from src.devai_analytics.database import Base, DatabaseManager
from src.devai_analytics.models import DevelopmentSession, AIInteraction
from src.devai_analytics.ai_providers.config import ProvidersConfig, ProviderConfig
from src.devai_analytics.ai_providers.base_provider import ProviderType


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def test_db_manager(temp_db_path):
    """Create a test database manager with temporary database."""
    db_manager = DatabaseManager(f"sqlite:///{temp_db_path}")
    db_manager.create_tables()
    yield db_manager
    db_manager.close()


@pytest.fixture
def test_db_session(test_db_manager):
    """Create a test database session."""
    session = test_db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_session():
    """Create a sample development session."""
    return DevelopmentSession(
        session_id="test_session_001",
        start_time=datetime.utcnow() - timedelta(hours=2),
        project_path="/test/project",
        user_id="test_user",
        claude_version="claude-3-sonnet"
    )


@pytest.fixture
def sample_interactions():
    """Create sample AI interactions."""
    base_time = datetime.utcnow() - timedelta(hours=1)
    
    return [
        AIInteraction(
            interaction_id="interaction_001",
            session_id="test_session_001",
            timestamp=base_time,
            request_tokens=150,
            response_tokens=300,
            model_name="claude-3-sonnet",
            prompt_type="code_analysis",
            response_time_ms=1200.5
        ),
        AIInteraction(
            interaction_id="interaction_002",
            session_id="test_session_001",
            timestamp=base_time + timedelta(minutes=10),
            request_tokens=200,
            response_tokens=400,
            model_name="gpt-4o",
            prompt_type="code_generation",
            response_time_ms=1500.2
        ),
        AIInteraction(
            interaction_id="interaction_003",
            session_id="test_session_001",
            timestamp=base_time + timedelta(minutes=20),
            request_tokens=100,
            response_tokens=250,
            model_name="claude-3-haiku",
            prompt_type="review",
            response_time_ms=800.0
        )
    ]


@pytest.fixture
def test_providers_config():
    """Create a test providers configuration."""
    config = ProvidersConfig()
    
    # Override with test configurations
    config._configs[ProviderType.OPENAI] = ProviderConfig(
        provider_type=ProviderType.OPENAI,
        enabled=True,
        api_key="test_openai_key",
        organization_id="test_org",
        collection_interval_hours=1
    )
    
    config._configs[ProviderType.CLAUDE] = ProviderConfig(
        provider_type=ProviderType.CLAUDE,
        enabled=True,
        api_key="test_claude_key",
        collection_interval_hours=1
    )
    
    return config


@pytest.fixture
def mock_openai_usage_data():
    """Sample OpenAI usage data."""
    return [
        {
            "date": "2024-01-15",
            "model": "gpt-4o",
            "requests": 25,
            "input_tokens": 5000,
            "output_tokens": 2500,
            "organization_id": "org-test"
        },
        {
            "date": "2024-01-15",
            "model": "gpt-4",
            "requests": 15,
            "input_tokens": 3000,
            "output_tokens": 1500,
            "organization_id": "org-test"
        }
    ]


@pytest.fixture
def mock_claude_usage_data():
    """Sample Claude usage data."""
    return [
        {
            "date": "2024-01-15",
            "model": "claude-3-5-sonnet",
            "requests": 20,
            "input_tokens": 4000,
            "output_tokens": 2000,
            "organization_id": "org-claude-test"
        },
        {
            "date": "2024-01-15",
            "model": "claude-3-haiku",
            "requests": 30,
            "input_tokens": 2000,
            "output_tokens": 1000,
            "organization_id": "org-claude-test"
        }
    ]


@pytest.fixture
def mock_telemetry_events():
    """Sample telemetry events."""
    return [
        {
            "event_id": "metric_001",
            "event_type": "metric",
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": "test_session_001",
            "data": {
                "metric_name": "claude_code.request",
                "value": 1,
                "attributes": {
                    "model": "claude-3-sonnet",
                    "tokens": 450
                }
            }
        },
        {
            "event_id": "trace_001",
            "event_type": "trace",
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": "test_session_001",
            "data": {
                "span_name": "ai_request",
                "duration_ms": 1250,
                "attributes": {
                    "model": "claude-3-sonnet",
                    "request_tokens": 150,
                    "response_tokens": 300
                }
            }
        }
    ]


# Performance test data
@pytest.fixture
def large_session_dataset():
    """Generate a large dataset for performance testing."""
    sessions = []
    interactions = []
    
    base_time = datetime.utcnow() - timedelta(days=30)
    
    for i in range(100):  # 100 sessions
        session_id = f"perf_session_{i:03d}"
        session_start = base_time + timedelta(hours=i * 2)
        
        session = DevelopmentSession(
            session_id=session_id,
            start_time=session_start,
            end_time=session_start + timedelta(hours=1),
            project_path=f"/test/project_{i % 10}",
            user_id=f"user_{i % 5}",
            claude_version="claude-3-sonnet"
        )
        sessions.append(session)
        
        # 10 interactions per session
        for j in range(10):
            interaction = AIInteraction(
                interaction_id=f"perf_interaction_{i:03d}_{j:02d}",
                session_id=session_id,
                timestamp=session_start + timedelta(minutes=j * 5),
                request_tokens=100 + (j * 20),
                response_tokens=200 + (j * 30),
                model_name=["claude-3-sonnet", "gpt-4o", "claude-3-haiku"][j % 3],
                prompt_type=["analysis", "generation", "review"][j % 3],
                response_time_ms=800 + (j * 100)
            )
            interactions.append(interaction)
    
    return sessions, interactions