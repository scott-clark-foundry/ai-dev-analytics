# AI Development Analytics - Project Details

## Tech Stack
- Python 3.11 with type hints
- FastAPI for REST API
- SQLAlchemy 2.0 + Alembic for data layer
- SQLite for local storage
- Click for CLI interface
- Pytest for testing

## Development Commands
    # Virtual environment
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    
    # Install deps
    pip install -r requirements.txt
    
    # Run server
    uvicorn src.main:app --reload
    
    # Run tests
    pytest -v
    
    # Quality checks
    black src/ tests/
    ruff check src/ tests/
    mypy src/ --strict

## Project Structure
    src/
    ├── api/              # FastAPI endpoints
    ├── core/             # Business logic
    ├── infrastructure/   # Database, git
    ├── services/         # Analytics, reporting
    └── cli/              # CLI commands

## Key Patterns
- Repository pattern for data access
- Dependency injection via FastAPI
- Async where beneficial
- Type hints throughout

## Environment
    DATABASE_URL=sqlite:///./ai_dev_analytics.db
    LOG_LEVEL=info
    IDLE_TIMEOUT_MINUTES=15

## Performance Targets
- API response <50ms
- Report generation <2s
- Support 10K+ sessions