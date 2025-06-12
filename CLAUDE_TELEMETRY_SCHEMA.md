# Claude Code Telemetry Schema

This document describes the complete OpenTelemetry schema for Claude Code telemetry data.

## Configuration

### Environment Variables
```bash
# Enable telemetry
export CLAUDE_CODE_ENABLE_TELEMETRY=1

# Configure exporters  
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp

# Configure endpoint
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Optional: Faster export intervals for development
export OTEL_METRIC_EXPORT_INTERVAL=5000
export OTEL_LOGS_EXPORT_INTERVAL=5000
```

## Metrics

Claude Code exports 7 different metrics via OpenTelemetry:

### 1. `claude_code.session.count`
- **Description**: Count of CLI sessions started
- **Unit**: count
- **Type**: Sum
- **Attributes**: Standard session attributes

### 2. `claude_code.cost.usage` ✅ **Implemented**
- **Description**: Cost of the Claude Code session
- **Unit**: USD
- **Type**: Sum
- **Attributes**:
  - `model`: Model used (e.g., "claude-3-5-haiku-20241022", "claude-sonnet-4-20250514")
  - Standard session attributes

### 3. `claude_code.token.usage` ✅ **Implemented**
- **Description**: Number of tokens used
- **Unit**: tokens
- **Type**: Sum
- **Attributes**:
  - `type`: Token type ("input", "output", "cacheRead", "cacheCreation")
  - `model`: Model used
  - Standard session attributes

### 4. `claude_code.lines_of_code.count` ✅ **Implemented**
- **Description**: Count of lines of code modified, with the 'type' attribute indicating whether lines were added or removed
- **Unit**: count
- **Type**: Sum
- **Attributes**:
  - `type`: Change type ("added", "removed")
  - Standard session attributes

### 5. `claude_code.code_edit_tool.decision` ✅ **Implemented**
- **Description**: Count of code editing tool permission decisions (accept/reject) for Edit, MultiEdit, Write, and NotebookEdit tools
- **Unit**: count
- **Type**: Sum
- **Attributes**:
  - `tool_name`: Tool used ("Edit", "MultiEdit", "Write", "NotebookEdit")
  - `decision`: User decision ("accept", "reject")
  - `source`: Permission source ("user_temporary", "user_permanent", "config", "user_abort", "user_reject")
  - Standard session attributes

### 6. `claude_code.pull_request.count` ❓ **Available but requires PR creation**
- **Description**: Number of pull requests created
- **Unit**: count
- **Type**: Sum
- **Attributes**: Standard session attributes

### 7. `claude_code.commit.count` ❓ **Available but requires commits**
- **Description**: Number of git commits created
- **Unit**: count
- **Type**: Sum
- **Attributes**: Standard session attributes

## Standard Attributes

All metrics include these standard attributes in their data points:

- `session.id`: Unique session identifier (e.g., "f12d59a8-5008-4cd9-aacd-70a16b1fbbd4")
- `user.id`: Hashed user identifier
- `user.email`: User email address
- `user.account_uuid`: User account UUID
- `organization.id`: Organization identifier

## Resource Attributes

All metrics include these resource-level attributes:

- `service.name`: Always "claude-code"
- `service.version`: Claude Code version (e.g., "1.0.17")

## Logs/Events ✅ **Implemented**

Claude Code also exports log events via OpenTelemetry logs protocol. These contain:

- **Body**: Event description/message
- **Severity**: Log level (INFO, WARN, ERROR, etc.)
- **Attributes**: Event-specific attributes
- **Resource Attributes**: Same as metrics
- **Timestamps**: Event timing information

Common log events include:
- User prompts (length, optional content)
- Tool execution results
- API request details
- API errors
- Tool permission decisions

## Data Types

### Metric Types
- **Sum**: Cumulative metrics that increase over time
- **Aggregation Temporality**: Cumulative
- **Monotonic**: True (values only increase)

### Value Types
- **Double**: Floating-point values (costs, some counts)
- **Integer**: Whole number values (token counts, line counts)

## Implementation Status

### ✅ **Fully Implemented Metrics (4/7)**
1. `claude_code.cost.usage` - Cost tracking with model attribution
2. `claude_code.token.usage` - Token usage by type and model
3. `claude_code.lines_of_code.count` - Code change tracking
4. `claude_code.code_edit_tool.decision` - Tool permission tracking

### ❓ **Available But Context-Dependent (3/7)**
5. `claude_code.session.count` - May appear with fresh sessions
6. `claude_code.pull_request.count` - Requires PR creation actions
7. `claude_code.commit.count` - Requires git commit actions

### ✅ **Logs/Events**
- Log event processing implemented
- Events stored in session attributes
- Memory management (keeps last 50 events per session)

## Example Values

### Token Usage Data Point
```json
{
  "metric_name": "claude_code.token.usage",
  "value": 122,
  "attributes": {
    "type": "input",
    "model": "claude-3-5-haiku-20241022",
    "session.id": "f12d59a8-5008-4cd9-aacd-70a16b1fbbd4",
    "user.email": "user@example.com",
    "organization.id": "a1c80a5c-1304-43b4-ae23-3e403c95d9df"
  }
}
```

### Code Edit Tool Decision Data Point  
```json
{
  "metric_name": "claude_code.code_edit_tool.decision",
  "value": 1,
  "attributes": {
    "decision": "accept",
    "tool_name": "Edit",
    "source": "user_temporary",
    "session.id": "f12d59a8-5008-4cd9-aacd-70a16b1fbbd4"
  }
}
```

### Lines of Code Data Point
```json
{
  "metric_name": "claude_code.lines_of_code.count", 
  "value": 13,
  "attributes": {
    "type": "added",
    "session.id": "f12d59a8-5008-4cd9-aacd-70a16b1fbbd4"
  }
}
```

## Analytics Derived

From this telemetry data, our system calculates:

### Session Analytics
- Total cost per session
- Token efficiency (cache hit rates)
- Development productivity (net lines changed)
- Tool adoption patterns
- Model usage preferences

### Interaction Analytics  
- Cost per interaction
- Token usage patterns
- Response times (when available in traces)
- Model switching behavior

### Development Metrics
- Lines added/removed/net change
- Tool permission acceptance rates
- Git activity (commits, PRs)
- Session duration and frequency

## Reference

- **Official Documentation**: https://docs.anthropic.com/en/docs/claude-code/monitoring-usage
- **OpenTelemetry Specs**: https://opentelemetry.io/docs/specs/otel/
- **Protocol**: OTLP/gRPC on port 4317 (default)