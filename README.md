# AI Development Analytics

A real-time telemetry collector and analytics platform for AI-assisted development sessions, specifically designed to capture and analyze Claude Code usage patterns.

## Features

- **Real-time Telemetry Collection**: Captures OpenTelemetry data from Claude Code via OTLP/gRPC
- **Live Dashboard**: Console-based real-time display of development metrics
- **Comprehensive Analytics**: Tracks costs, token usage, code changes, and tool decisions
- **Session Management**: Organizes data by development sessions with detailed summaries
- **Demo Mode**: Built-in sample data generation for testing and demonstration

## Supported Metrics

The collector captures all available Claude Code telemetry metrics:

✅ **Active Metrics:**
- `claude_code.cost.usage` - Development costs by model
- `claude_code.token.usage` - Token consumption (input/output/cache)
- `claude_code.lines_of_code.count` - Code changes (added/removed)
- `claude_code.code_edit_tool.decision` - Tool permission decisions

📊 **Context-Dependent Metrics:**
- `claude_code.session.count` - CLI session tracking
- `claude_code.pull_request.count` - PR creation tracking
- `claude_code.commit.count` - Git commit tracking

## Quick Start

### Prerequisites
- Python 3.11+
- Claude Code with telemetry enabled

### Installation

```bash
# Clone repository
git clone https://github.com/scott-clark-foundry/ai-dev-analytics.git
cd ai-dev-analytics

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Enable Claude Code Telemetry

```bash
# Enable telemetry export
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Optional: Faster updates for development
export OTEL_METRIC_EXPORT_INTERVAL=5000
export OTEL_LOGS_EXPORT_INTERVAL=5000
```

### Run the Collector

```bash
# Start telemetry collector
python -m src.devai_analytics.cli

# Or run in demo mode (no Claude Code required)
python -m src.devai_analytics.cli --demo

# Custom port or host
python -m src.devai_analytics.cli --port 4318 --host 0.0.0.0
```

### Usage with Claude Code

1. Start the telemetry collector in one terminal
2. Run Claude Code in another terminal with telemetry enabled
3. Watch real-time analytics as you develop!

## Dashboard Display

The live dashboard shows:

```
🔥 AI DEVELOPMENT ANALYTICS - REAL-TIME DASHBOARD 🔥

📊 OVERVIEW
• Total Sessions: 1    • Active Sessions: 1    • Total Events: 89

💰 COST ANALYSIS
• Total Cost: $0.0234    • Avg Cost/Session: $0.0234

🔤 TOKEN METRICS  
• Total Tokens: 2,847    • Input: 2,405    • Output: 442
• Cache Efficiency: 0% hits    • Cache Created: 0

📝 CODE PRODUCTIVITY
• Lines Added: 215    • Lines Removed: 0    • Net Change: +215

🛠️ TOOL USAGE
• Edit Decisions: 12 (100% accepted)    • Tools Used: Edit, Write
```

## Project Structure

```
src/
├── devai_analytics/
│   ├── cli.py              # Main CLI application
│   ├── storage.py          # In-memory data storage
│   ├── display.py          # Console dashboard
│   ├── models.py           # Data models
│   ├── sample_data.py      # Demo data generator
│   └── telemetry/
│       ├── receiver.py     # OTLP gRPC receiver
│       └── processor.py    # Telemetry data processor
```

## CLI Options

```bash
python -m src.devai_analytics.cli --help

Options:
  --host TEXT           Host to bind OTLP receiver (default: localhost)
  --port INTEGER        Port for OTLP receiver (default: 4317)
  --demo               Run in demo mode with sample data
  --log-level TEXT     Set logging level (DEBUG, INFO, WARNING, ERROR)
  --log-file TEXT      Log to file (default: console only)
  --show-sessions      Show all captured sessions and exit
  --show-session TEXT  Show details for specific session ID and exit
```

## Development

### Running Tests
```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=src/devai_analytics tests/
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/ --strict
```

## Technical Details

- **Architecture**: Hexagonal (Ports & Adapters) pattern
- **Protocol**: OpenTelemetry OTLP over gRPC
- **Storage**: Thread-safe in-memory storage with session management
- **Display**: Real-time console dashboard with 2-second refresh
- **Data Models**: Structured session, interaction, and event tracking

## Telemetry Schema

See [CLAUDE_TELEMETRY_SCHEMA.md](CLAUDE_TELEMETRY_SCHEMA.md) for complete OpenTelemetry schema documentation including all metric types, attributes, and data formats.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Open an issue on GitHub
- Check the telemetry schema documentation
- Verify Claude Code telemetry configuration

## Roadmap

- [ ] SQLite persistence layer
- [ ] Web-based dashboard
- [ ] Export capabilities (JSON, CSV)
- [ ] Advanced analytics and insights
- [ ] Multi-session comparison
- [ ] Performance optimization metrics