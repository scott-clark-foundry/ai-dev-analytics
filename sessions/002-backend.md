# Session 002: API Backend Foundation

## Objective
Transform PoC telemetry consumer into a proper FastAPI backend service with data persistence and basic web interface.

## Task 1: Database Schema and Models (25 minutes)
### Subtasks
1.1 Create SQLite database schema for sessions and interactions tables
1.2 Implement SQLAlchemy models with proper relationships and constraints
1.3 Add database initialization and connection management
1.4 Create basic CRUD operations for sessions and interactions
1.5 Test database operations with sample data

## Task 2: FastAPI Service Architecture (35 minutes)
### Subtasks
2.1 Set up FastAPI application with proper project structure
2.2 Create API endpoints for telemetry ingestion and data retrieval
2.3 Integrate OpenTelemetry receiver with FastAPI background tasks
2.4 Add Pydantic schemas for request/response validation
2.5 Implement async database operations for performance

## Task 3: OpenAI Usage API Integration (30 minutes)
### Subtasks
3.1 Create OpenAI API client with proper authentication
3.2 Implement periodic data collection from Usage API endpoints
3.3 Map OpenAI usage data to internal session tracking
3.4 Add cost calculation logic using current OpenAI pricing
3.5 Store OpenAI data alongside Claude Code telemetry

## Task 4: Basic Web Dashboard (20 minutes)
### Subtasks
4.1 Create HTML template with Chart.js for data visualization
4.2 Add API endpoints to serve dashboard data in JSON format
4.3 Implement basic charts: usage over time, cost breakdown, session summary
4.4 Style with minimal CSS for clean, functional appearance
4.5 Test full data flow from telemetry capture to web display

## Success Criteria
- FastAPI server runs and handles concurrent telemetry ingestion
- SQLite database stores session and interaction data reliably
- OpenAI Usage API integration provides cost and token data
- Web dashboard displays real development session analytics
- All API endpoints respond correctly with proper error handling

## Notes
- Keep web interface simple - focus on data visualization, not UI polish
- Ensure background telemetry collection doesn't block API responses
- Test with real Claude Code and OpenAI API calls to validate data accuracy
- Use async/await consistently for database and API operations