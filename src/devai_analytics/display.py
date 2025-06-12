"""Console output formatter for displaying captured telemetry data."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .models import DevelopmentSession, AIInteraction, SessionSummary
from .storage import InMemoryStorage

logger = logging.getLogger(__name__)


class ConsoleFormatter:
    """Formats telemetry data for console display."""
    
    def __init__(self):
        self.colors = {
            'reset': '\033[0m',
            'bold': '\033[1m',
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m'
        }
    
    def colorize(self, text: str, color: str) -> str:
        """Apply color to text."""
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def format_header(self, title: str) -> str:
        """Format a section header."""
        separator = "=" * 60
        return f"\n{self.colorize(separator, 'blue')}\n{self.colorize(title.center(60), 'bold')}\n{self.colorize(separator, 'blue')}\n"
    
    def format_session_summary(self, session: DevelopmentSession) -> str:
        """Format a session summary for display."""
        status = self.colorize("ACTIVE", "green") if session.is_active else self.colorize("ENDED", "yellow")
        
        duration = "Ongoing"
        if session.total_duration_ms:
            duration_sec = session.total_duration_ms / 1000
            duration = f"{duration_sec:.1f}s"
        
        lines = [
            f"Session: {self.colorize(session.session_id, 'cyan')} [{status}]",
            f"  Started: {session.start_time.strftime('%H:%M:%S')}",
            f"  Duration: {duration}",
            f"  Interactions: {self.colorize(str(session.total_interactions), 'magenta')}",
            f"  Total Tokens: {self.colorize(str(session.total_tokens), 'yellow')}",
        ]
        
        if session.project_path:
            lines.append(f"  Project: {session.project_path}")
        
        if session.claude_version:
            lines.append(f"  Claude: {session.claude_version}")
        
        # Show cost if available
        cost = session.attributes.get('total_cost_usd')
        if cost:
            lines.append(f"  Cost: ${cost:.6f}")
        
        # Show user email if available
        user_email = session.attributes.get('user_email')
        if user_email:
            lines.append(f"  User: {user_email}")
        
        # Show lines of code changes
        lines_added = session.attributes.get('lines_added', 0)
        lines_removed = session.attributes.get('lines_removed', 0)
        if lines_added > 0 or lines_removed > 0:
            net_change = lines_added - lines_removed
            sign = "+" if net_change >= 0 else ""
            lines.append(f"  Code: {self.colorize(f'+{lines_added}', 'green')} {self.colorize(f'-{lines_removed}', 'red')} ({sign}{net_change} net)")
        
        # Show tool decisions
        tool_decisions = session.attributes.get('tool_decisions')
        if tool_decisions and tool_decisions['total'] > 0:
            accepted = tool_decisions['accepted']
            total = tool_decisions['total']
            tools_used = tool_decisions.get('tools_used_list', [])
            lines.append(f"  Tools: {accepted}/{total} accepted ({', '.join(tools_used)})")
        
        # Show git activity
        commits = session.attributes.get('commits_created', 0)
        prs = session.attributes.get('pull_requests_created', 0)
        if commits > 0 or prs > 0:
            git_parts = []
            if commits > 0:
                git_parts.append(f"{commits} commits")
            if prs > 0:
                git_parts.append(f"{prs} PRs")
            lines.append(f"  Git: {', '.join(git_parts)}")
        
        return "\n".join(lines)
    
    def format_interaction(self, interaction: AIInteraction) -> str:
        """Format an AI interaction for display."""
        timestamp = interaction.timestamp.strftime('%H:%M:%S')
        
        lines = [
            f"  {self.colorize('→', 'green')} {timestamp} - {interaction.interaction_id[:8]}",
            f"    Tokens: {interaction.request_tokens} → {interaction.response_tokens} (total: {interaction.total_tokens})"
        ]
        
        if interaction.model_name:
            lines.append(f"    Model: {interaction.model_name}")
        
        if interaction.response_time_ms:
            lines.append(f"    Response Time: {interaction.response_time_ms:.0f}ms")
        
        return "\n".join(lines)
    
    def format_statistics(self, stats: Dict[str, Any]) -> str:
        """Format overall statistics."""
        lines = [
            f"Total Sessions: {self.colorize(str(stats['total_sessions']), 'cyan')}",
            f"Active Sessions: {self.colorize(str(stats['active_sessions']), 'green')}",
            f"Total Interactions: {self.colorize(str(stats['total_interactions']), 'magenta')}",
            f"Total Tokens: {self.colorize(str(stats['total_tokens']), 'yellow')}",
            f"Total Events: {self.colorize(str(stats['total_events']), 'blue')}"
        ]
        return "\n".join(lines)
    
    def format_session_list(self, sessions: List[DevelopmentSession]) -> str:
        """Format a list of sessions."""
        if not sessions:
            return self.colorize("No sessions found", "yellow")
        
        output = []
        for session in sessions:
            output.append(self.format_session_summary(session))
            
            # Show recent interactions
            if session.interactions:
                recent_interactions = sorted(session.interactions, key=lambda x: x.timestamp, reverse=True)[:3]
                output.append(self.colorize("  Recent Interactions:", "bold"))
                for interaction in recent_interactions:
                    output.append(self.format_interaction(interaction))
            
            output.append("")  # Empty line between sessions
        
        return "\n".join(output)


class RealTimeDisplay:
    """Real-time display manager for telemetry data."""
    
    def __init__(self, storage: InMemoryStorage):
        self.storage = storage
        self.formatter = ConsoleFormatter()
        self.last_update = datetime.now()
        self.update_interval = timedelta(seconds=2)
    
    def should_update(self) -> bool:
        """Check if display should be updated."""
        return datetime.now() - self.last_update >= self.update_interval
    
    def clear_screen(self):
        """Clear the console screen."""
        print("\033[2J\033[H", end="")
    
    def display_dashboard(self):
        """Display the main dashboard."""
        if not self.should_update():
            return
        
        self.clear_screen()
        
        # Header
        print(self.formatter.format_header("AI Development Analytics - Live Dashboard"))
        
        # Statistics
        stats = self.storage.get_total_stats()
        print(self.formatter.format_statistics(stats))
        
        # Active Sessions
        active_sessions = self.storage.get_active_sessions()
        if active_sessions:
            print(self.formatter.format_header("Active Sessions"))
            print(self.formatter.format_session_list(active_sessions))
        
        # Recent Sessions
        all_sessions = self.storage.get_sessions()
        if all_sessions:
            recent_sessions = sorted(all_sessions, key=lambda x: x.start_time, reverse=True)[:5]
            print(self.formatter.format_header("Recent Sessions"))
            print(self.formatter.format_session_list(recent_sessions))
        
        # Footer
        print(f"\n{self.formatter.colorize('Last Updated: ' + datetime.now().strftime('%H:%M:%S'), 'blue')}")
        print(f"{self.formatter.colorize('Press Ctrl+C to stop', 'red')}")
        
        self.last_update = datetime.now()
    
    def display_session_details(self, session_id: str):
        """Display detailed information for a specific session."""
        session = self.storage.get_session(session_id)
        if not session:
            print(self.formatter.colorize(f"Session {session_id} not found", "red"))
            return
        
        print(self.formatter.format_header(f"Session Details: {session_id}"))
        print(self.formatter.format_session_summary(session))
        
        if session.interactions:
            print(self.formatter.format_header("All Interactions"))
            for interaction in sorted(session.interactions, key=lambda x: x.timestamp):
                print(self.formatter.format_interaction(interaction))
    
    def display_summary(self):
        """Display a summary of all sessions."""
        print(self.formatter.format_header("Session Summary"))
        
        summaries = self.storage.get_session_summaries()
        if not summaries:
            print(self.formatter.colorize("No sessions found", "yellow"))
            return
        
        # Sort by start time
        summaries.sort(key=lambda x: x.start_time, reverse=True)
        
        for summary in summaries:
            status = self.formatter.colorize("ACTIVE", "green") if summary.end_time is None else self.formatter.colorize("ENDED", "yellow")
            duration = f"{summary.duration_minutes:.1f}m" if summary.duration_minutes else "Ongoing"
            
            print(f"{self.formatter.colorize(summary.session_id, 'cyan')} [{status}]")
            print(f"  Time: {summary.start_time.strftime('%Y-%m-%d %H:%M:%S')} ({duration})")
            print(f"  Tokens: {self.formatter.colorize(str(summary.total_tokens), 'yellow')}")
            print(f"  Interactions: {summary.total_interactions}")
            if summary.models_used:
                print(f"  Models: {', '.join(summary.models_used)}")
            if summary.project_path:
                print(f"  Project: {summary.project_path}")
            print()


def print_welcome():
    """Print welcome message."""
    formatter = ConsoleFormatter()
    print(formatter.format_header("AI Development Analytics - Telemetry Consumer"))
    print(formatter.colorize("Starting Claude Code telemetry collection...", "green"))
    print(formatter.colorize("Listening for OpenTelemetry data on localhost:4317", "blue"))
    print()


def print_startup_info():
    """Print startup information and instructions."""
    formatter = ConsoleFormatter()
    print(formatter.colorize("Setup Instructions:", "bold"))
    print("1. Enable Claude Code telemetry:")
    print(formatter.colorize("   export CLAUDE_CODE_ENABLE_TELEMETRY=1", "cyan"))
    print("2. Start using Claude Code in another terminal")
    print("3. Telemetry data will appear here automatically")
    print()
    print(formatter.colorize("Commands:", "bold"))
    print("  Ctrl+C  - Stop the collector")
    print("  The display updates every 2 seconds")
    print()