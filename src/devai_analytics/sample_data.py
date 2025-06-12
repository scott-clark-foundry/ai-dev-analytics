"""Generate sample telemetry data for testing when Claude Code isn't available."""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from .models import DevelopmentSession, AIInteraction


class SampleDataGenerator:
    """Generates realistic sample telemetry data for testing."""
    
    def __init__(self):
        self.model_names = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022", 
            "claude-3-opus-20240229"
        ]
        
        self.prompt_types = [
            "code_generation",
            "code_explanation",
            "debugging",
            "refactoring",
            "documentation",
            "testing",
            "general"
        ]
        
        self.project_paths = [
            "/home/user/projects/web-app",
            "/home/user/projects/api-service", 
            "/home/user/projects/data-pipeline",
            "/home/user/projects/mobile-app"
        ]
    
    def generate_session(self, session_id: str = None, num_interactions: int = None) -> DevelopmentSession:
        """Generate a realistic development session."""
        if session_id is None:
            session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"
        
        if num_interactions is None:
            num_interactions = random.randint(3, 15)
        
        # Session timing
        start_time = datetime.now() - timedelta(
            minutes=random.randint(5, 120),
            seconds=random.randint(0, 59)
        )
        
        session = DevelopmentSession(
            session_id=session_id,
            start_time=start_time,
            project_path=random.choice(self.project_paths),
            user_id=f"user_{random.randint(1, 100)}",
            claude_version="claude-code-v1.2.3",
            attributes={
                "environment": "development",
                "ide": "vscode",
                "language": random.choice(["python", "javascript", "typescript", "java", "go"])
            }
        )
        
        # Generate interactions
        current_time = start_time
        for i in range(num_interactions):
            interaction = self._generate_interaction(session_id, current_time, i)
            session.add_interaction(interaction)
            
            # Advance time for next interaction
            current_time += timedelta(
                minutes=random.randint(1, 10),
                seconds=random.randint(0, 59)
            )
        
        # Randomly end session or keep active
        if random.random() < 0.7:  # 70% chance session is ended
            session.end_session(current_time)
        
        return session
    
    def _generate_interaction(self, session_id: str, timestamp: datetime, index: int) -> AIInteraction:
        """Generate a realistic AI interaction."""
        model_name = random.choice(self.model_names)
        prompt_type = random.choice(self.prompt_types)
        
        # Token counts based on prompt type
        if prompt_type == "code_generation":
            request_tokens = random.randint(100, 500)
            response_tokens = random.randint(200, 1000)
        elif prompt_type == "code_explanation":
            request_tokens = random.randint(150, 800)
            response_tokens = random.randint(100, 600)
        elif prompt_type == "debugging":
            request_tokens = random.randint(200, 600)
            response_tokens = random.randint(150, 400)
        else:
            request_tokens = random.randint(50, 300)
            response_tokens = random.randint(50, 400)
        
        # Response time varies by model and complexity
        if "opus" in model_name:
            response_time = random.randint(2000, 8000)  # Slower but higher quality
        elif "haiku" in model_name:
            response_time = random.randint(500, 2000)   # Faster
        else:
            response_time = random.randint(1000, 4000)  # Sonnet
        
        return AIInteraction(
            interaction_id=f"{session_id}_interaction_{index}",
            session_id=session_id,
            timestamp=timestamp,
            request_tokens=request_tokens,
            response_tokens=response_tokens,
            model_name=model_name,
            prompt_type=prompt_type,
            response_time_ms=response_time,
            attributes={
                "tool_use": random.choice([True, False]),
                "context_length": random.randint(1000, 10000),
                "temperature": round(random.uniform(0.0, 1.0), 2)
            }
        )
    
    def generate_metric_data(self, session: DevelopmentSession, interaction: AIInteraction) -> List[Dict[str, Any]]:
        """Generate OpenTelemetry metric data format - returns multiple metrics."""
        base_attrs = {
            'interaction.id': interaction.interaction_id,
            'model.name': interaction.model_name,
            'prompt.type': interaction.prompt_type
        }
        
        resource_attrs = {
            'session.id': session.session_id,
            'claude.version': session.claude_version,
            'project.path': session.project_path,
            'user.id': session.user_id
        }
        
        # Generate separate metrics for request, response, and total tokens
        metrics = []
        
        # Request tokens metric
        metrics.append({
            'name': 'claude.tokens.request',
            'description': 'Request tokens used in AI interaction',
            'unit': 'token',
            'scope': 'claude-code',
            'resource_attributes': resource_attrs,
            'timestamp': interaction.timestamp.isoformat(),
            'data_points': [{
                'attributes': base_attrs,
                'start_time': interaction.timestamp.isoformat(),
                'time': interaction.timestamp.isoformat(),
                'value': interaction.request_tokens
            }]
        })
        
        # Response tokens metric
        metrics.append({
            'name': 'claude.tokens.response',
            'description': 'Response tokens used in AI interaction',
            'unit': 'token',
            'scope': 'claude-code',
            'resource_attributes': resource_attrs,
            'timestamp': interaction.timestamp.isoformat(),
            'data_points': [{
                'attributes': base_attrs,
                'start_time': interaction.timestamp.isoformat(),
                'time': interaction.timestamp.isoformat(),
                'value': interaction.response_tokens
            }]
        })
        
        # Total tokens metric
        metrics.append({
            'name': 'claude.tokens.total',
            'description': 'Total tokens used in AI interaction',
            'unit': 'token',
            'scope': 'claude-code',
            'resource_attributes': resource_attrs,
            'timestamp': interaction.timestamp.isoformat(),
            'data_points': [{
                'attributes': base_attrs,
                'start_time': interaction.timestamp.isoformat(),
                'time': interaction.timestamp.isoformat(),
                'value': interaction.total_tokens
            }]
        })
        
        return metrics
    
    def generate_trace_data(self, session: DevelopmentSession, interaction: AIInteraction) -> Dict[str, Any]:
        """Generate OpenTelemetry trace data format."""
        return {
            'trace_id': f"trace_{interaction.interaction_id}",
            'span_id': f"span_{interaction.interaction_id}",
            'parent_span_id': None,
            'name': 'claude_ai_interaction',
            'kind': 1,  # SPAN_KIND_INTERNAL
            'start_time': interaction.timestamp.isoformat(),
            'end_time': (interaction.timestamp + timedelta(milliseconds=interaction.response_time_ms)).isoformat(),
            'duration_ms': interaction.response_time_ms,
            'attributes': {
                'interaction.id': interaction.interaction_id,
                'model.name': interaction.model_name,
                'prompt.type': interaction.prompt_type,
                'tokens.request': interaction.request_tokens,
                'tokens.response': interaction.response_tokens,
                'tokens.total': interaction.total_tokens
            },
            'resource_attributes': {
                'session.id': session.session_id,
                'claude.version': session.claude_version,
                'project.path': session.project_path,
                'user.id': session.user_id
            },
            'scope': 'claude-code',
            'status': {
                'code': 1,  # STATUS_CODE_OK
                'message': 'completed'
            }
        }
    
    def generate_continuous_data(self, storage_callback, interval_seconds: int = 5, num_sessions: int = 3):
        """Generate continuous sample data for testing real-time display."""
        import threading
        import time
        
        sessions = []
        for i in range(num_sessions):
            session = self.generate_session(f"demo_session_{i+1}", num_interactions=2)
            sessions.append(session)
            
            # Add initial data
            for interaction in session.interactions:
                metrics_list = self.generate_metric_data(session, interaction)
                trace_data = self.generate_trace_data(session, interaction)
                
                # Store each metric separately
                for metric_data in metrics_list:
                    storage_callback('metric', metric_data)
                storage_callback('trace', trace_data)
        
        def generate_new_interactions():
            """Generate new interactions periodically."""
            while True:
                time.sleep(interval_seconds)
                
                # Add new interaction to a random active session
                active_sessions = [s for s in sessions if s.is_active]
                if active_sessions:
                    session = random.choice(active_sessions)
                    
                    # Generate new interaction
                    interaction = self._generate_interaction(
                        session.session_id,
                        datetime.now(),
                        len(session.interactions)
                    )
                    
                    # Generate telemetry data
                    metrics_list = self.generate_metric_data(session, interaction)
                    trace_data = self.generate_trace_data(session, interaction)
                    
                    # Store each metric separately
                    for metric_data in metrics_list:
                        storage_callback('metric', metric_data)
                    storage_callback('trace', trace_data)
                    
                    # Randomly end session
                    if len(session.interactions) > 8 and random.random() < 0.3:
                        session.end_session()
        
        # Start background thread
        thread = threading.Thread(target=generate_new_interactions, daemon=True)
        thread.start()
        
        return sessions


def create_sample_sessions(num_sessions: int = 5) -> List[DevelopmentSession]:
    """Create a list of sample sessions for testing."""
    generator = SampleDataGenerator()
    sessions = []
    
    for i in range(num_sessions):
        session = generator.generate_session(f"sample_session_{i+1}")
        sessions.append(session)
    
    return sessions