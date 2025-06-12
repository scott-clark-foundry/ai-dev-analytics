"""Configuration for AI provider integrations."""

import os
from dataclasses import dataclass
from typing import Dict, Optional, Set
from .base_provider import ProviderType


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    
    provider_type: ProviderType
    enabled: bool
    api_key: Optional[str] = None
    organization_id: Optional[str] = None
    collection_interval_hours: int = 6
    max_retry_attempts: int = 3
    timeout_seconds: int = 30
    custom_settings: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.enabled and not self.api_key:
            # Try to get API key from environment
            env_key = f"{self.provider_type.value.upper()}_API_KEY"
            self.api_key = os.getenv(env_key)
            
        if self.custom_settings is None:
            self.custom_settings = {}


class ProvidersConfig:
    """Configuration manager for all AI providers."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        self._configs: Dict[ProviderType, ProviderConfig] = {}
        self._load_from_environment()
    
    def _load_from_environment(self):
        """Load provider configurations from environment variables."""
        
        # OpenAI Configuration
        openai_enabled = os.getenv("OPENAI_ENABLED", "true").lower() == "true"
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_org_id = os.getenv("OPENAI_ORG_ID")
        
        self._configs[ProviderType.OPENAI] = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            enabled=openai_enabled and bool(openai_api_key),
            api_key=openai_api_key,
            organization_id=openai_org_id,
            collection_interval_hours=int(os.getenv("OPENAI_COLLECTION_INTERVAL", "6")),
            custom_settings={
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "timeout": os.getenv("OPENAI_TIMEOUT", "30")
            }
        )
        
        # Claude/Anthropic Configuration
        claude_enabled = os.getenv("CLAUDE_ENABLED", "true").lower() == "true"
        claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        self._configs[ProviderType.CLAUDE] = ProviderConfig(
            provider_type=ProviderType.CLAUDE,
            enabled=claude_enabled and bool(claude_api_key),
            api_key=claude_api_key,
            collection_interval_hours=int(os.getenv("CLAUDE_COLLECTION_INTERVAL", "6")),
            custom_settings={
                "base_url": os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
                "timeout": os.getenv("ANTHROPIC_TIMEOUT", "30"),
                "max_tokens_per_request": os.getenv("ANTHROPIC_MAX_TOKENS", "4096")
            }
        )
        
        # Gemini Configuration (placeholder for future)
        gemini_enabled = os.getenv("GEMINI_ENABLED", "false").lower() == "true"
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        self._configs[ProviderType.GEMINI] = ProviderConfig(
            provider_type=ProviderType.GEMINI,
            enabled=gemini_enabled and bool(gemini_api_key),
            api_key=gemini_api_key,
            collection_interval_hours=int(os.getenv("GEMINI_COLLECTION_INTERVAL", "6")),
            custom_settings={
                "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "region": os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
            }
        )
        
        # Cohere Configuration (placeholder for future)
        cohere_enabled = os.getenv("COHERE_ENABLED", "false").lower() == "true"
        cohere_api_key = os.getenv("COHERE_API_KEY")
        
        self._configs[ProviderType.COHERE] = ProviderConfig(
            provider_type=ProviderType.COHERE,
            enabled=cohere_enabled and bool(cohere_api_key),
            api_key=cohere_api_key,
            collection_interval_hours=int(os.getenv("COHERE_COLLECTION_INTERVAL", "6"))
        )
    
    def get_config(self, provider_type: ProviderType) -> ProviderConfig:
        """Get configuration for a specific provider."""
        return self._configs.get(provider_type, ProviderConfig(
            provider_type=provider_type,
            enabled=False
        ))
    
    def get_enabled_providers(self) -> Set[ProviderType]:
        """Get set of enabled provider types."""
        return {
            provider_type for provider_type, config in self._configs.items()
            if config.enabled
        }
    
    def is_provider_enabled(self, provider_type: ProviderType) -> bool:
        """Check if a specific provider is enabled."""
        config = self.get_config(provider_type)
        return config.enabled
    
    def update_config(self, provider_type: ProviderType, **kwargs):
        """Update configuration for a provider."""
        if provider_type not in self._configs:
            self._configs[provider_type] = ProviderConfig(
                provider_type=provider_type,
                enabled=False
            )
        
        config = self._configs[provider_type]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    def get_all_configs(self) -> Dict[ProviderType, ProviderConfig]:
        """Get all provider configurations."""
        return self._configs.copy()
    
    def validate_configs(self) -> Dict[ProviderType, Dict[str, str]]:
        """Validate all provider configurations and return any issues."""
        issues = {}
        
        for provider_type, config in self._configs.items():
            provider_issues = []
            
            if config.enabled:
                if not config.api_key:
                    provider_issues.append("API key is required but not provided")
                
                if config.collection_interval_hours < 1:
                    provider_issues.append("Collection interval must be at least 1 hour")
                
                if config.max_retry_attempts < 0:
                    provider_issues.append("Max retry attempts must be non-negative")
                
                if config.timeout_seconds < 1:
                    provider_issues.append("Timeout must be at least 1 second")
            
            if provider_issues:
                issues[provider_type] = provider_issues
        
        return issues
    
    def get_summary(self) -> Dict[str, any]:
        """Get a summary of provider configurations."""
        enabled_count = len(self.get_enabled_providers())
        total_count = len(self._configs)
        
        return {
            "total_providers": total_count,
            "enabled_providers": enabled_count,
            "disabled_providers": total_count - enabled_count,
            "provider_status": {
                provider_type.value: config.enabled 
                for provider_type, config in self._configs.items()
            },
            "collection_intervals": {
                provider_type.value: config.collection_interval_hours
                for provider_type, config in self._configs.items()
                if config.enabled
            }
        }


# Global configuration instance
_providers_config: Optional[ProvidersConfig] = None


def get_providers_config() -> ProvidersConfig:
    """Get the global providers configuration instance."""
    global _providers_config
    if _providers_config is None:
        _providers_config = ProvidersConfig()
    return _providers_config


def reload_config():
    """Reload configuration from environment variables."""
    global _providers_config
    _providers_config = ProvidersConfig()