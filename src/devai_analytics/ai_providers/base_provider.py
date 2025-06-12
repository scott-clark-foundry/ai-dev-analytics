"""Abstract base class for AI provider integrations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Supported AI provider types."""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    COHERE = "cohere"


@dataclass
class UsageRecord:
    """Standardized usage record across all providers."""
    
    provider: ProviderType
    date: date
    model: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    organization_id: Optional[str] = None
    session_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Ensure total_tokens is calculated."""
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class ProviderUsageSummary:
    """Summary of usage for a provider over a time period."""
    
    provider: ProviderType
    period_days: int
    total_cost: float
    total_tokens: int
    total_requests: int
    by_model: Dict[str, Dict[str, Any]]
    daily_breakdown: List[Dict[str, Any]]


class BaseAIProvider(ABC):
    """Abstract base class for AI provider integrations."""
    
    def __init__(self, provider_type: ProviderType, enabled: bool = True):
        """Initialize base provider."""
        self.provider_type = provider_type
        self.enabled = enabled
        self._running = False
        self._collection_task = None
        
    @property
    def is_enabled(self) -> bool:
        """Check if provider is enabled."""
        return self.enabled
        
    @property
    def is_running(self) -> bool:
        """Check if provider is currently running."""
        return self._running
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider (authenticate, validate config, etc.)."""
        pass
        
    @abstractmethod
    async def start_collection(self, interval_hours: int = 6) -> None:
        """Start periodic usage data collection."""
        pass
        
    @abstractmethod
    async def stop_collection(self) -> None:
        """Stop periodic usage data collection."""
        pass
        
    @abstractmethod
    async def collect_usage_data(self, days_back: int = 1) -> List[UsageRecord]:
        """Collect usage data for the specified period."""
        pass
        
    @abstractmethod
    async def get_usage_summary(self, days: int = 7) -> ProviderUsageSummary:
        """Get usage summary for the specified period."""
        pass
        
    @abstractmethod
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for given model and token usage."""
        pass
        
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """Get list of supported models for this provider."""
        pass
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the provider."""
        try:
            await self.initialize()
            return {
                "provider": self.provider_type.value,
                "status": "healthy",
                "enabled": self.enabled,
                "running": self._running
            }
        except Exception as e:
            logger.error(f"Health check failed for {self.provider_type.value}: {e}")
            return {
                "provider": self.provider_type.value,
                "status": "unhealthy",
                "enabled": self.enabled,
                "running": self._running,
                "error": str(e)
            }
    
    def __str__(self) -> str:
        """String representation of provider."""
        return f"{self.provider_type.value.title()}Provider(enabled={self.enabled}, running={self._running})"
        
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"{self.__class__.__name__}("
                f"provider_type={self.provider_type}, "
                f"enabled={self.enabled}, "
                f"running={self._running})")


class ProviderError(Exception):
    """Base exception for provider-related errors."""
    
    def __init__(self, provider: ProviderType, message: str, cause: Optional[Exception] = None):
        self.provider = provider
        self.message = message
        self.cause = cause
        super().__init__(f"{provider.value}: {message}")


class ProviderInitializationError(ProviderError):
    """Raised when provider initialization fails."""
    pass


class ProviderCollectionError(ProviderError):
    """Raised when usage data collection fails."""
    pass


class ProviderAuthenticationError(ProviderError):
    """Raised when provider authentication fails."""
    pass