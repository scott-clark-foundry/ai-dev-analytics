"""Claude/Anthropic provider implementation for usage tracking."""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
import anthropic

from .base_provider import (
    BaseAIProvider, ProviderType, UsageRecord, ProviderUsageSummary,
    ProviderInitializationError, ProviderCollectionError, ProviderAuthenticationError
)
from .config import ProviderConfig
from ..database import get_db_session, ClaudeUsageModel
from ..repository import SessionRepository

logger = logging.getLogger(__name__)


class ClaudePricingCalculator:
    """Calculate costs based on Claude/Anthropic pricing."""
    
    # Current Claude pricing (as of December 2024)
    PRICING = {
        "claude-3-haiku": {
            "input": 0.00025,   # per 1K tokens
            "output": 0.00125   # per 1K tokens
        },
        "claude-3-sonnet": {
            "input": 0.003,
            "output": 0.015
        },
        "claude-3-opus": {
            "input": 0.015,
            "output": 0.075
        },
        "claude-3-5-sonnet": {
            "input": 0.003,
            "output": 0.015
        },
        "claude-3-5-haiku": {
            "input": 0.001,
            "output": 0.005
        },
        # Legacy models
        "claude-2.1": {
            "input": 0.008,
            "output": 0.024
        },
        "claude-2": {
            "input": 0.008,
            "output": 0.024
        },
        "claude-instant-1.2": {
            "input": 0.0008,
            "output": 0.0024
        }
    }
    
    @classmethod
    def calculate_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for given model and token usage."""
        # Normalize model name for pricing lookup
        model_key = model.lower()
        if model_key not in cls.PRICING:
            # Try to match partial model names
            for price_model in cls.PRICING:
                if price_model in model_key or model_key in price_model:
                    model_key = price_model
                    break
            else:
                # Default to claude-3-sonnet pricing for unknown models
                model_key = "claude-3-sonnet"
                logger.warning(f"Unknown Claude model '{model}', using claude-3-sonnet pricing")
            
        pricing = cls.PRICING[model_key]
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost


class ClaudeProvider(BaseAIProvider):
    """Claude/Anthropic provider implementation."""
    
    def __init__(self, config: ProviderConfig):
        """Initialize Claude provider."""
        super().__init__(ProviderType.CLAUDE, config.enabled)
        self.config = config
        self.client: Optional[anthropic.AsyncAnthropic] = None
        self.pricing_calculator = ClaudePricingCalculator()
    
    async def initialize(self) -> bool:
        """Initialize the Claude client."""
        try:
            if not self.config.api_key:
                raise ProviderAuthenticationError(
                    self.provider_type,
                    "Anthropic API key not provided"
                )
            
            self.client = anthropic.AsyncAnthropic(
                api_key=self.config.api_key,
                timeout=self.config.timeout_seconds,
                base_url=self.config.custom_settings.get("base_url", "https://api.anthropic.com")
            )
            
            # Test the connection - we can't easily test without usage, so we'll just validate client creation
            logger.info("Claude provider initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Claude provider: {e}")
            raise ProviderInitializationError(
                self.provider_type,
                f"Failed to initialize: {str(e)}",
                e
            )
    
    async def start_collection(self, interval_hours: int = None) -> None:
        """Start periodic usage data collection."""
        if not await self.initialize():
            raise ProviderInitializationError(self.provider_type, "Failed to initialize provider")
        
        interval = interval_hours or self.config.collection_interval_hours
        self._running = True
        self._collection_task = asyncio.create_task(
            self._periodic_collection_loop(interval)
        )
        logger.info(f"Started Claude usage collection (every {interval} hours)")
    
    async def stop_collection(self) -> None:
        """Stop periodic usage data collection."""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped Claude usage collection")
    
    async def _periodic_collection_loop(self, interval_hours: int):
        """Run periodic collection loop."""
        while self._running:
            try:
                await self.collect_usage_data()
                await asyncio.sleep(interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Claude periodic collection: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def collect_usage_data(self, days_back: int = 1) -> List[UsageRecord]:
        """Collect usage data from Claude API."""
        try:
            logger.info(f"Collecting Claude usage data for last {days_back} days")
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days_back)
            
            # Get usage data from Claude API
            raw_usage_data = await self._fetch_usage_from_api(start_date, end_date)
            
            if not raw_usage_data:
                logger.warning("No usage data received from Claude API")
                return []
            
            # Convert to standardized UsageRecord format
            usage_records = []
            for raw_record in raw_usage_data:
                record = await self._convert_to_usage_record(raw_record)
                if record:
                    usage_records.append(record)
            
            # Store in database
            await self._store_usage_records(usage_records)
            
            logger.info(f"Collected and stored {len(usage_records)} Claude usage records")
            return usage_records
            
        except Exception as e:
            logger.error(f"Error collecting Claude usage data: {e}")
            raise ProviderCollectionError(
                self.provider_type,
                f"Failed to collect usage data: {str(e)}",
                e
            )
    
    async def _fetch_usage_from_api(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Fetch usage data from Claude API."""
        try:
            # Note: Anthropic doesn't have a public usage API endpoint yet
            # This is a placeholder for when the API becomes available
            # For now, we'll simulate usage data collection
            
            logger.warning("Claude Usage API not yet available - using simulated data")
            return await self._generate_simulated_usage_data(start_date, end_date)
            
        except Exception as e:
            logger.error(f"Error fetching from Claude API: {e}")
            return []
    
    async def _generate_simulated_usage_data(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Generate simulated usage data for testing."""
        simulated_data = []
        
        current_date = start_date
        while current_date <= end_date:
            # Simulate some usage for each model
            for model in ["claude-3-5-sonnet", "claude-3-haiku", "claude-3-sonnet"]:
                usage_record = {
                    "date": current_date.isoformat(),
                    "model": model,
                    "requests": 5 + (hash(f"{current_date}_{model}") % 25),
                    "input_tokens": 800 + (hash(f"{current_date}_{model}_input") % 3000),
                    "output_tokens": 400 + (hash(f"{current_date}_{model}_output") % 1500),
                    "organization_id": "org-claude-example"
                }
                simulated_data.append(usage_record)
            
            current_date += timedelta(days=1)
        
        return simulated_data
    
    async def _convert_to_usage_record(self, raw_record: Dict[str, Any]) -> Optional[UsageRecord]:
        """Convert raw API response to standardized UsageRecord."""
        try:
            date_str = raw_record.get("date")
            model = raw_record.get("model")
            requests = raw_record.get("requests", 0)
            input_tokens = raw_record.get("input_tokens", 0)
            output_tokens = raw_record.get("output_tokens", 0)
            
            # Calculate cost
            cost_usd = self.calculate_cost(model, input_tokens, output_tokens)
            
            # Try to map to existing session
            session_id = await self._map_to_session(date_str, model)
            
            return UsageRecord(
                provider=ProviderType.CLAUDE,
                date=datetime.fromisoformat(date_str).date(),
                model=model,
                requests=requests,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost_usd=cost_usd,
                organization_id=raw_record.get("organization_id"),
                session_id=session_id,
                raw_data=raw_record
            )
            
        except Exception as e:
            logger.error(f"Error converting Claude usage record: {e}")
            return None
    
    async def _store_usage_records(self, records: List[UsageRecord]):
        """Store usage records in database."""
        db = get_db_session()
        try:
            for record in records:
                db_record = ClaudeUsageModel(
                    session_id=record.session_id,
                    date=datetime.combine(record.date, datetime.min.time()),
                    organization_id=record.organization_id,
                    model=record.model,
                    requests=record.requests,
                    tokens=record.total_tokens,
                    cost_usd=record.cost_usd,
                    raw_data=record.raw_data
                )
                db.add(db_record)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing Claude usage records: {e}")
            raise
        finally:
            db.close()
    
    async def _map_to_session(self, date_str: str, model: str) -> Optional[str]:
        """Try to map Claude usage to existing sessions."""
        try:
            usage_date = datetime.fromisoformat(date_str).date()
            
            # Find sessions from the same day
            db = get_db_session()
            session_repo = SessionRepository(db)
            
            try:
                sessions = session_repo.list_sessions(limit=100)
                
                # Look for sessions on the same day that used Claude models
                for session in sessions:
                    if session.start_time.date() == usage_date:
                        # Simple heuristic: if session has interactions with Claude models
                        for interaction in session.interactions:
                            if (interaction.model_name and 
                                ("claude" in interaction.model_name.lower() or 
                                 "sonnet" in interaction.model_name.lower())):
                                return session.session_id
                
                return None
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error mapping Claude usage to session: {e}")
            return None
    
    async def get_usage_summary(self, days: int = 7) -> ProviderUsageSummary:
        """Get usage summary for the specified period."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            db = get_db_session()
            try:
                # Get usage records for the period
                usage_records = (db.query(ClaudeUsageModel)
                               .filter(ClaudeUsageModel.date >= start_date)
                               .all())
                
                if not usage_records:
                    return ProviderUsageSummary(
                        provider=ProviderType.CLAUDE,
                        period_days=days,
                        total_cost=0.0,
                        total_tokens=0,
                        total_requests=0,
                        by_model={},
                        daily_breakdown=[]
                    )
                
                total_cost = sum(record.cost_usd for record in usage_records)
                total_tokens = sum(record.tokens for record in usage_records)
                total_requests = sum(record.requests for record in usage_records)
                
                # Group by model
                by_model = {}
                for record in usage_records:
                    model = record.model
                    if model not in by_model:
                        by_model[model] = {
                            "cost": 0.0,
                            "tokens": 0,
                            "requests": 0
                        }
                    by_model[model]["cost"] += record.cost_usd
                    by_model[model]["tokens"] += record.tokens
                    by_model[model]["requests"] += record.requests
                
                # Daily breakdown
                daily_breakdown = {}
                for record in usage_records:
                    date_key = record.date.date().isoformat()
                    if date_key not in daily_breakdown:
                        daily_breakdown[date_key] = {
                            "cost": 0.0,
                            "tokens": 0,
                            "requests": 0
                        }
                    daily_breakdown[date_key]["cost"] += record.cost_usd
                    daily_breakdown[date_key]["tokens"] += record.tokens
                    daily_breakdown[date_key]["requests"] += record.requests
                
                return ProviderUsageSummary(
                    provider=ProviderType.CLAUDE,
                    period_days=days,
                    total_cost=total_cost,
                    total_tokens=total_tokens,
                    total_requests=total_requests,
                    by_model=by_model,
                    daily_breakdown=[
                        {"date": date, **stats}
                        for date, stats in sorted(daily_breakdown.items())
                    ]
                )
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error getting Claude usage summary: {e}")
            return ProviderUsageSummary(
                provider=ProviderType.CLAUDE,
                period_days=days,
                total_cost=0.0,
                total_tokens=0,
                total_requests=0,
                by_model={},
                daily_breakdown=[]
            )
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for given model and token usage."""
        return self.pricing_calculator.calculate_cost(model, input_tokens, output_tokens)
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported Claude models."""
        return list(self.pricing_calculator.PRICING.keys())