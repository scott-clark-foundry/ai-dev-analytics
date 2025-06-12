"""Provider manager for orchestrating multiple AI providers."""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta

from .base_provider import BaseAIProvider, ProviderType, UsageRecord, ProviderUsageSummary
from .config import ProvidersConfig, get_providers_config
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    """Manages multiple AI provider integrations."""
    
    def __init__(self, config: Optional[ProvidersConfig] = None):
        """Initialize provider manager."""
        self.config = config or get_providers_config()
        self.providers: Dict[ProviderType, BaseAIProvider] = {}
        self._initialized = False
    
    async def initialize(self) -> Dict[ProviderType, bool]:
        """Initialize all enabled providers."""
        initialization_results = {}
        
        for provider_type in self.config.get_enabled_providers():
            try:
                provider = self._create_provider(provider_type)
                if provider:
                    success = await provider.initialize()
                    if success:
                        self.providers[provider_type] = provider
                        initialization_results[provider_type] = True
                        logger.info(f"Successfully initialized {provider_type.value} provider")
                    else:
                        initialization_results[provider_type] = False
                        logger.error(f"Failed to initialize {provider_type.value} provider")
                else:
                    initialization_results[provider_type] = False
                    logger.error(f"Failed to create {provider_type.value} provider")
                    
            except Exception as e:
                initialization_results[provider_type] = False
                logger.error(f"Error initializing {provider_type.value} provider: {e}")
        
        self._initialized = True
        logger.info(f"Provider manager initialized with {len(self.providers)} active providers")
        return initialization_results
    
    def _create_provider(self, provider_type: ProviderType) -> Optional[BaseAIProvider]:
        """Create a provider instance based on type."""
        config = self.config.get_config(provider_type)
        
        if provider_type == ProviderType.OPENAI:
            return OpenAIProvider(config)
        elif provider_type == ProviderType.CLAUDE:
            return ClaudeProvider(config)
        elif provider_type == ProviderType.GEMINI:
            # Placeholder for future Gemini provider
            logger.warning("Gemini provider not yet implemented")
            return None
        elif provider_type == ProviderType.COHERE:
            # Placeholder for future Cohere provider
            logger.warning("Cohere provider not yet implemented")
            return None
        else:
            logger.error(f"Unknown provider type: {provider_type}")
            return None
    
    async def start_all_collections(self) -> Dict[ProviderType, bool]:
        """Start data collection for all providers."""
        if not self._initialized:
            await self.initialize()
        
        start_results = {}
        
        for provider_type, provider in self.providers.items():
            try:
                config = self.config.get_config(provider_type)
                await provider.start_collection(config.collection_interval_hours)
                start_results[provider_type] = True
                logger.info(f"Started collection for {provider_type.value} provider")
            except Exception as e:
                start_results[provider_type] = False
                logger.error(f"Failed to start collection for {provider_type.value}: {e}")
        
        return start_results
    
    async def stop_all_collections(self) -> Dict[ProviderType, bool]:
        """Stop data collection for all providers."""
        stop_results = {}
        
        for provider_type, provider in self.providers.items():
            try:
                await provider.stop_collection()
                stop_results[provider_type] = True
                logger.info(f"Stopped collection for {provider_type.value} provider")
            except Exception as e:
                stop_results[provider_type] = False
                logger.error(f"Failed to stop collection for {provider_type.value}: {e}")
        
        return stop_results
    
    async def collect_all_usage_data(self, days_back: int = 1) -> Dict[ProviderType, List[UsageRecord]]:
        """Collect usage data from all providers."""
        if not self._initialized:
            await self.initialize()
        
        results = {}
        
        # Collect from all providers concurrently
        tasks = []
        provider_types = []
        
        for provider_type, provider in self.providers.items():
            tasks.append(provider.collect_usage_data(days_back))
            provider_types.append(provider_type)
        
        if tasks:
            try:
                collection_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for provider_type, result in zip(provider_types, collection_results):
                    if isinstance(result, Exception):
                        logger.error(f"Error collecting from {provider_type.value}: {result}")
                        results[provider_type] = []
                    else:
                        results[provider_type] = result
                        logger.info(f"Collected {len(result)} records from {provider_type.value}")
            except Exception as e:
                logger.error(f"Error in concurrent collection: {e}")
                # Fallback to sequential collection
                for provider_type, provider in self.providers.items():
                    try:
                        records = await provider.collect_usage_data(days_back)
                        results[provider_type] = records
                    except Exception as provider_error:
                        logger.error(f"Error collecting from {provider_type.value}: {provider_error}")
                        results[provider_type] = []
        
        return results
    
    async def get_all_usage_summaries(self, days: int = 7) -> Dict[ProviderType, ProviderUsageSummary]:
        """Get usage summaries from all providers."""
        if not self._initialized:
            await self.initialize()
        
        results = {}
        
        # Get summaries from all providers concurrently
        tasks = []
        provider_types = []
        
        for provider_type, provider in self.providers.items():
            tasks.append(provider.get_usage_summary(days))
            provider_types.append(provider_type)
        
        if tasks:
            try:
                summary_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for provider_type, result in zip(provider_types, summary_results):
                    if isinstance(result, Exception):
                        logger.error(f"Error getting summary from {provider_type.value}: {result}")
                        # Create empty summary
                        results[provider_type] = ProviderUsageSummary(
                            provider=provider_type,
                            period_days=days,
                            total_cost=0.0,
                            total_tokens=0,
                            total_requests=0,
                            by_model={},
                            daily_breakdown=[]
                        )
                    else:
                        results[provider_type] = result
            except Exception as e:
                logger.error(f"Error in concurrent summary collection: {e}")
        
        return results
    
    async def get_provider_health_checks(self) -> Dict[ProviderType, Dict[str, Any]]:
        """Get health check status for all providers."""
        health_checks = {}
        
        for provider_type, provider in self.providers.items():
            try:
                health_check = await provider.health_check()
                health_checks[provider_type] = health_check
            except Exception as e:
                health_checks[provider_type] = {
                    "provider": provider_type.value,
                    "status": "error",
                    "error": str(e)
                }
        
        # Also check configured but uninitialized providers
        for provider_type in self.config.get_enabled_providers():
            if provider_type not in health_checks:
                health_checks[provider_type] = {
                    "provider": provider_type.value,
                    "status": "not_initialized",
                    "enabled": True,
                    "running": False
                }
        
        return health_checks
    
    def get_active_providers(self) -> Set[ProviderType]:
        """Get set of currently active provider types."""
        return set(self.providers.keys())
    
    def get_provider(self, provider_type: ProviderType) -> Optional[BaseAIProvider]:
        """Get a specific provider instance."""
        return self.providers.get(provider_type)
    
    def is_provider_active(self, provider_type: ProviderType) -> bool:
        """Check if a specific provider is active."""
        return provider_type in self.providers
    
    async def add_provider(self, provider_type: ProviderType) -> bool:
        """Add and initialize a new provider."""
        if provider_type in self.providers:
            logger.warning(f"Provider {provider_type.value} is already active")
            return True
        
        try:
            provider = self._create_provider(provider_type)
            if provider and await provider.initialize():
                self.providers[provider_type] = provider
                logger.info(f"Successfully added {provider_type.value} provider")
                return True
            else:
                logger.error(f"Failed to add {provider_type.value} provider")
                return False
        except Exception as e:
            logger.error(f"Error adding {provider_type.value} provider: {e}")
            return False
    
    async def remove_provider(self, provider_type: ProviderType) -> bool:
        """Remove a provider and stop its collection."""
        if provider_type not in self.providers:
            logger.warning(f"Provider {provider_type.value} is not active")
            return True
        
        try:
            provider = self.providers[provider_type]
            await provider.stop_collection()
            del self.providers[provider_type]
            logger.info(f"Successfully removed {provider_type.value} provider")
            return True
        except Exception as e:
            logger.error(f"Error removing {provider_type.value} provider: {e}")
            return False
    
    def get_manager_summary(self) -> Dict[str, Any]:
        """Get summary of provider manager status."""
        active_providers = list(self.get_active_providers())
        running_providers = [
            provider_type for provider_type, provider in self.providers.items()
            if provider.is_running
        ]
        
        return {
            "initialized": self._initialized,
            "total_configured": len(self.config.get_enabled_providers()),
            "total_active": len(active_providers),
            "total_running": len(running_providers),
            "active_providers": [p.value for p in active_providers],
            "running_providers": [p.value for p in running_providers],
            "config_summary": self.config.get_summary()
        }


# Global provider manager instance
_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Get the global provider manager instance."""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


async def initialize_providers() -> Dict[ProviderType, bool]:
    """Initialize all providers."""
    manager = get_provider_manager()
    return await manager.initialize()


async def start_all_provider_collections() -> Dict[ProviderType, bool]:
    """Start collection for all providers."""
    manager = get_provider_manager()
    return await manager.start_all_collections()


async def stop_all_provider_collections() -> Dict[ProviderType, bool]:
    """Stop collection for all providers."""
    manager = get_provider_manager()
    return await manager.stop_all_collections()