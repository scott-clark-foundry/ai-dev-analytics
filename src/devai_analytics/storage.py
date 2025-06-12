"""Simple in-memory storage for captured telemetry data."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from threading import Lock
from .models import DevelopmentSession, AIInteraction, TelemetryEvent, SessionSummary

logger = logging.getLogger(__name__)


class InMemoryStorage:
    """Thread-safe in-memory storage for telemetry data."""
    
    def __init__(self):
        self._lock = Lock()
        self._sessions: Dict[str, DevelopmentSession] = {}
        self._events: List[TelemetryEvent] = []
        self._interactions: Dict[str, AIInteraction] = {}
    
    def store_event(self, event_type: str, event_data: Dict[str, Any]):
        """Store a raw telemetry event."""
        with self._lock:
            try:
                if event_type == 'metric':
                    event = TelemetryEvent.from_metric(event_data)
                elif event_type == 'trace':
                    event = TelemetryEvent.from_trace(event_data)
                elif event_type == 'log':
                    event = TelemetryEvent.from_log(event_data)
                else:
                    logger.warning(f"Unknown event type: {event_type}")
                    return
                
                self._events.append(event)
                
                # Debug logging
                logger.info(f"Processing {event_type} event: {event_data.get('name', 'unknown')}")
                logger.debug(f"Event data: {event_data}")
                
                self._process_event(event)
                
                logger.debug(f"Stored {event_type} event: {event.event_id}")
                
            except Exception as e:
                logger.error(f"Error storing event: {e}", exc_info=True)
    
    def _process_event(self, event: TelemetryEvent):
        """Process a telemetry event and update session/interaction data."""
        try:
            if event.event_type == 'metric':
                self._process_metric_event(event)
            elif event.event_type == 'trace':
                self._process_trace_event(event)
            elif event.event_type == 'log':
                self._process_log_event(event)
                
            event.processed = True
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {e}")
    
    def _process_metric_event(self, event: TelemetryEvent):
        """Process a metric event to extract session/interaction data."""
        data = event.data
        metric_name = data.get('name', '')
        
        logger.info(f"Processing metric: {metric_name}")
        
        # Extract session information from resource attributes
        resource_attrs = data.get('resource_attributes', {})
        session_id = resource_attrs.get('session.id')
        
        logger.info(f"Session ID: {session_id}")
        
        if not session_id:
            logger.warning(f"No session ID found in resource attributes: {resource_attrs}")
            return
        
        # Ensure session exists
        self._ensure_session(session_id, resource_attrs)
        logger.info(f"Session ensured: {session_id}")
        
        # Process Claude Code specific metrics
        if metric_name == 'claude_code.token.usage':
            logger.info(f"Processing token metric for session {session_id}")
            self._process_claude_token_metric(event, session_id)
        elif metric_name == 'claude_code.cost.usage':
            logger.info(f"Processing cost metric for session {session_id}")
            self._process_claude_cost_metric(event, session_id)
        elif metric_name == 'claude_code.lines_of_code.count':
            logger.info(f"Processing lines of code metric for session {session_id}")
            self._process_lines_of_code_metric(event, session_id)
        elif metric_name == 'claude_code.code_edit_tool.decision':
            logger.info(f"Processing code edit tool decision metric for session {session_id}")
            self._process_tool_decision_metric(event, session_id)
        elif metric_name == 'claude_code.session.count':
            logger.info(f"Processing session count metric for session {session_id}")
            self._process_session_count_metric(event, session_id)
        elif metric_name == 'claude_code.pull_request.count':
            logger.info(f"Processing pull request metric for session {session_id}")
            self._process_pull_request_metric(event, session_id)
        elif metric_name == 'claude_code.commit.count':
            logger.info(f"Processing commit metric for session {session_id}")
            self._process_commit_metric(event, session_id)
        else:
            logger.info(f"Unhandled metric: {metric_name}")
    
    def _process_trace_event(self, event: TelemetryEvent):
        """Process a trace event to extract interaction data."""
        data = event.data
        
        # Extract session information from resource attributes
        resource_attrs = data.get('resource_attributes', {})
        session_id = resource_attrs.get('session.id') or resource_attrs.get('claude.session_id')
        
        if not session_id:
            return
        
        # Ensure session exists
        self._ensure_session(session_id, resource_attrs)
        
        # Create or update AI interaction from trace
        if 'ai_interaction' in data.get('name', '').lower() or 'claude' in data.get('name', '').lower():
            self._process_ai_interaction_trace(event, session_id)
    
    def _ensure_session(self, session_id: str, resource_attrs: Dict[str, Any]):
        """Ensure a session exists in storage."""
        if session_id not in self._sessions:
            self._sessions[session_id] = DevelopmentSession(
                session_id=session_id,
                start_time=datetime.utcnow(),
                project_path=resource_attrs.get('project.path'),  # Claude Code might not send this
                user_id=resource_attrs.get('user.id'),
                claude_version=resource_attrs.get('service.version', 'unknown'),
                attributes={
                    'service_name': resource_attrs.get('service.name'),
                    'user_email': resource_attrs.get('user.email'),
                    'organization_id': resource_attrs.get('organization.id'),
                    'user_account_uuid': resource_attrs.get('user.account_uuid'),
                    **resource_attrs
                }
            )
    
    def _process_claude_token_metric(self, event: TelemetryEvent, session_id: str):
        """Process Claude Code token usage metrics."""
        data = event.data
        session = self._sessions[session_id]
        
        # Group data points by model and interaction
        model_tokens = {}
        
        for data_point in data.get('data_points', []):
            value = data_point.get('value', 0)
            attrs = data_point.get('attributes', {})
            
            model = attrs.get('model', 'unknown')
            token_type = attrs.get('type', 'unknown')
            
            if model not in model_tokens:
                model_tokens[model] = {
                    'input': 0,
                    'output': 0,
                    'cacheRead': 0,
                    'cacheCreation': 0
                }
            
            if token_type in model_tokens[model]:
                model_tokens[model][token_type] = int(value)
        
        # Create interactions for each model used
        for model, tokens in model_tokens.items():
            if tokens['input'] > 0 or tokens['output'] > 0:
                # Create unique interaction ID
                interaction_id = f"{session_id}_{model}_{event.timestamp.timestamp()}"
                
                # Check if interaction already exists
                existing_interaction = next(
                    (i for i in session.interactions if i.interaction_id == interaction_id),
                    None
                )
                
                if not existing_interaction:
                    interaction = AIInteraction(
                        interaction_id=interaction_id,
                        session_id=session_id,
                        timestamp=event.timestamp,
                        request_tokens=tokens['input'],
                        response_tokens=tokens['output'],
                        total_tokens=tokens['input'] + tokens['output'],
                        model_name=model,
                        attributes={
                            'cache_read_tokens': tokens['cacheRead'],
                            'cache_creation_tokens': tokens['cacheCreation'],
                            **data.get('resource_attributes', {})
                        }
                    )
                    session.add_interaction(interaction)
                    self._interactions[interaction_id] = interaction
                else:
                    # Update existing interaction
                    existing_interaction.request_tokens += tokens['input']
                    existing_interaction.response_tokens += tokens['output']
                    existing_interaction.total_tokens = existing_interaction.request_tokens + existing_interaction.response_tokens
                    
                    # Recalculate session totals
                    session.total_tokens = sum(i.total_tokens for i in session.interactions)
                    session.total_request_tokens = sum(i.request_tokens for i in session.interactions)
                    session.total_response_tokens = sum(i.response_tokens for i in session.interactions)
    
    def _process_claude_cost_metric(self, event: TelemetryEvent, session_id: str):
        """Process Claude Code cost usage metrics."""
        data = event.data
        session = self._sessions[session_id]
        
        total_cost = 0
        for data_point in data.get('data_points', []):
            value = data_point.get('value', 0)
            total_cost += value
        
        # Add cost information to session attributes
        session.attributes['total_cost_usd'] = total_cost
    
    def _process_lines_of_code_metric(self, event: TelemetryEvent, session_id: str):
        """Process lines of code count metrics."""
        data = event.data
        session = self._sessions[session_id]
        
        lines_added = 0
        lines_removed = 0
        
        for data_point in data.get('data_points', []):
            value = int(data_point.get('value', 0))
            attrs = data_point.get('attributes', {})
            line_type = attrs.get('type', 'unknown')
            
            if line_type == 'added':
                lines_added += value
            elif line_type == 'removed':
                lines_removed += value
        
        # Update session with code change statistics
        if 'lines_added' not in session.attributes:
            session.attributes['lines_added'] = 0
        if 'lines_removed' not in session.attributes:
            session.attributes['lines_removed'] = 0
            
        session.attributes['lines_added'] += lines_added
        session.attributes['lines_removed'] += lines_removed
        session.attributes['lines_net_change'] = session.attributes['lines_added'] - session.attributes['lines_removed']
    
    def _process_tool_decision_metric(self, event: TelemetryEvent, session_id: str):
        """Process code edit tool decision metrics."""
        data = event.data
        session = self._sessions[session_id]
        
        if 'tool_decisions' not in session.attributes:
            session.attributes['tool_decisions'] = {
                'total': 0,
                'accepted': 0,
                'rejected': 0,
                'tools_used_list': [],
                'decisions_by_tool': {}
            }
        
        for data_point in data.get('data_points', []):
            attrs = data_point.get('attributes', {})
            decision = attrs.get('decision', 'unknown')
            tool_name = attrs.get('tool_name', 'unknown')
            source = attrs.get('source', 'unknown')
            
            session.attributes['tool_decisions']['total'] += 1
            
            if decision == 'accept':
                session.attributes['tool_decisions']['accepted'] += 1
            elif decision == 'reject':
                session.attributes['tool_decisions']['rejected'] += 1
            
            if 'tools_used_list' not in session.attributes['tool_decisions']:
                session.attributes['tool_decisions']['tools_used_list'] = []
            if tool_name not in session.attributes['tool_decisions']['tools_used_list']:
                session.attributes['tool_decisions']['tools_used_list'].append(tool_name)
            
            if tool_name not in session.attributes['tool_decisions']['decisions_by_tool']:
                session.attributes['tool_decisions']['decisions_by_tool'][tool_name] = {
                    'accepted': 0, 'rejected': 0
                }
            
            if decision in ['accept', 'reject']:
                session.attributes['tool_decisions']['decisions_by_tool'][tool_name][decision + 'ed'] += 1
    
    def _process_session_count_metric(self, event: TelemetryEvent, session_id: str):
        """Process session count metrics."""
        data = event.data
        session = self._sessions[session_id]
        
        # This tracks the number of CLI sessions started
        for data_point in data.get('data_points', []):
            value = int(data_point.get('value', 0))
            session.attributes['session_count'] = value
    
    def _process_pull_request_metric(self, event: TelemetryEvent, session_id: str):
        """Process pull request count metrics."""
        data = event.data
        session = self._sessions[session_id]
        
        total_prs = 0
        for data_point in data.get('data_points', []):
            value = int(data_point.get('value', 0))
            total_prs += value
        
        session.attributes['pull_requests_created'] = session.attributes.get('pull_requests_created', 0) + total_prs
    
    def _process_commit_metric(self, event: TelemetryEvent, session_id: str):
        """Process commit count metrics."""
        data = event.data
        session = self._sessions[session_id]
        
        total_commits = 0
        for data_point in data.get('data_points', []):
            value = int(data_point.get('value', 0))
            total_commits += value
        
        session.attributes['commits_created'] = session.attributes.get('commits_created', 0) + total_commits
    
    def _process_claude_metric(self, event: TelemetryEvent, session_id: str):
        """Process Claude Code specific metrics."""
        data = event.data
        session = self._sessions[session_id]
        
        # Update session attributes with Claude-specific data
        for data_point in data.get('data_points', []):
            attrs = data_point.get('attributes', {})
            session.attributes.update(attrs)
    
    def _process_ai_interaction_trace(self, event: TelemetryEvent, session_id: str):
        """Process AI interaction traces."""
        data = event.data
        
        interaction_id = data.get('span_id', f"{session_id}_{event.timestamp.timestamp()}")
        
        if interaction_id in self._interactions:
            interaction = self._interactions[interaction_id]
        else:
            interaction = AIInteraction(
                interaction_id=interaction_id,
                session_id=session_id,
                timestamp=event.timestamp,
                attributes=data.get('attributes', {})
            )
            self._interactions[interaction_id] = interaction
        
        # Update interaction timing
        if data.get('duration_ms'):
            interaction.response_time_ms = data['duration_ms']
        
        # Update model info from trace attributes
        attrs = data.get('attributes', {})
        if attrs.get('model.name'):
            interaction.model_name = attrs['model.name']
        
        # Add to session if not already present
        session = self._sessions[session_id]
        existing_interaction = next(
            (i for i in session.interactions if i.interaction_id == interaction.interaction_id),
            None
        )
        if not existing_interaction:
            session.add_interaction(interaction)
    
    def _process_log_event(self, event: TelemetryEvent):
        """Process a log event to extract session/interaction data."""
        data = event.data
        
        logger.info(f"Processing log event with body: {data.get('body', 'no body')}")
        
        # Extract session information from resource attributes
        resource_attrs = data.get('resource_attributes', {})
        session_id = resource_attrs.get('session.id')
        
        if session_id:
            # Ensure session exists
            self._ensure_session(session_id, resource_attrs)
            
            # Process different types of log events
            log_body = data.get('body', '')
            log_attrs = data.get('attributes', {})
            
            # Add log events to session for potential analysis
            session = self._sessions[session_id]
            if 'log_events' not in session.attributes:
                session.attributes['log_events'] = []
            
            session.attributes['log_events'].append({
                'timestamp': data.get('timestamp'),
                'severity': data.get('severity_text', 'INFO'),
                'body': log_body,
                'attributes': log_attrs
            })
            
            # Keep only recent log events to avoid memory bloat
            if len(session.attributes['log_events']) > 100:
                session.attributes['log_events'] = session.attributes['log_events'][-50:]
    
    def get_sessions(self) -> List[DevelopmentSession]:
        """Get all development sessions."""
        with self._lock:
            return list(self._sessions.values())
    
    def get_session(self, session_id: str) -> Optional[DevelopmentSession]:
        """Get a specific session by ID."""
        with self._lock:
            return self._sessions.get(session_id)
    
    def get_active_sessions(self) -> List[DevelopmentSession]:
        """Get all currently active sessions."""
        with self._lock:
            return [session for session in self._sessions.values() if session.is_active]
    
    def get_session_summaries(self) -> List[SessionSummary]:
        """Get summaries of all sessions."""
        with self._lock:
            return [SessionSummary.from_session(session) for session in self._sessions.values()]
    
    def get_events(self, limit: Optional[int] = None) -> List[TelemetryEvent]:
        """Get telemetry events."""
        with self._lock:
            events = sorted(self._events, key=lambda e: e.timestamp, reverse=True)
            if limit:
                events = events[:limit]
            return events
    
    def get_total_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        with self._lock:
            total_sessions = len(self._sessions)
            active_sessions = len([s for s in self._sessions.values() if s.is_active])
            total_interactions = sum(s.total_interactions for s in self._sessions.values())
            total_tokens = sum(s.total_tokens for s in self._sessions.values())
            
            return {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'total_interactions': total_interactions,
                'total_tokens': total_tokens,
                'total_events': len(self._events)
            }
    
    def clear(self):
        """Clear all stored data."""
        with self._lock:
            self._sessions.clear()
            self._events.clear()
            self._interactions.clear()
            logger.info("Storage cleared")