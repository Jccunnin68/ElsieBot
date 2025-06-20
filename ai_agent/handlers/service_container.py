"""
Service Container - Dependency Injection
========================================

This module provides a service container for managing dependencies and eliminating 
global variables throughout the codebase. It uses dependency injection to provide
clean, testable, and modular code.
"""

from typing import Dict, Any, Optional, Callable, TypeVar, Type, TYPE_CHECKING
import threading
from contextlib import contextmanager

# Forward references for type hints
if TYPE_CHECKING:
    from .ai_attention.state_manager import RoleplayStateManager
    from .ai_knowledge.database_controller import FleetDatabaseController
    from .ai_emotion.emotion_engine import EmotionEngine
    from .ai_attention.attention_engine import AttentionEngine
    from .ai_logic.logic_engine import LogicEngine
    from .ai_knowledge.knowledge_engine import KnowledgeEngine
    from .ai_wisdom.structured_content_retriever import StructuredContentRetriever
    from .ai_coordinator.ai_engine import AIEngine
    from .ai_emotion.greeting_service import GreetingService
    from .ai_emotion.drink_service import DrinkService
    from .ai_emotion.poetic_service import PoeticResponseService
    from .ai_logic.context_analysis_service import ContextAnalysisService
    from .utilities.date_conversion_service import DateConversionService
    from .utilities.content_filter_service import ContentFilterService
    from .utilities.text_utility_service import TextUtilityService
    from .ai_attention.character_tracking_service import CharacterTrackingService
    from .ai_attention.roleplay_exit_service import RoleplayExitService
    from .ai_wisdom.context_coordination_service import ContextCoordinationService

T = TypeVar('T')

class ServiceContainer:
    """
    A simple dependency injection container that manages service instances
    and eliminates the need for global variables.
    """
    
    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._singletons: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def register_singleton(self, name: str, factory: Callable[[], T]) -> None:
        """Register a singleton service with a factory function."""
        with self._lock:
            self._factories[name] = factory
    
    def register_instance(self, name: str, instance: Any) -> None:
        """Register a specific instance."""
        with self._lock:
            self._services[name] = instance
    
    def get(self, name: str) -> Any:
        """Get a service instance."""
        # Check if we have a direct instance
        if name in self._services:
            return self._services[name]
        
        # Check if we have a singleton that's already been created
        if name in self._singletons:
            return self._singletons[name]
        
        # Create singleton if we have a factory
        if name in self._factories:
            with self._lock:
                # Double-check pattern for thread safety
                if name not in self._singletons:
                    self._singletons[name] = self._factories[name]()
                return self._singletons[name]
        
        raise KeyError(f"Service '{name}' not found in container")
    
    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services or name in self._factories or name in self._singletons
    
    def clear(self) -> None:
        """Clear all services (useful for testing)."""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()
    
    @contextmanager
    def override(self, name: str, instance: Any):
        """Temporarily override a service (useful for testing)."""
        original = None
        had_original = False
        
        if name in self._services:
            original = self._services[name]
            had_original = True
        elif name in self._singletons:
            original = self._singletons[name]
            had_original = True
        
        # Set the override
        self._services[name] = instance
        
        try:
            yield
        finally:
            # Restore original
            if had_original:
                if name in self._services:
                    self._services[name] = original
                if name in self._singletons:
                    self._singletons[name] = original
            else:
                self._services.pop(name, None)
                self._singletons.pop(name, None)


# Global container instance - this is the only global we need
_container = ServiceContainer()

def get_container() -> ServiceContainer:
    """Get the global service container."""
    return _container

def register_default_services() -> None:
    """Register all default services with the container."""
    # Import here to avoid circular dependencies
    from .ai_attention.state_manager import RoleplayStateManager
    from .ai_knowledge.database_controller import FleetDatabaseController
    from .ai_emotion.emotion_engine import EmotionEngine
    from .ai_attention.attention_engine import AttentionEngine
    from .ai_logic.logic_engine import LogicEngine
    from .ai_knowledge.knowledge_engine import KnowledgeEngine
    from .ai_wisdom.structured_content_retriever import StructuredContentRetriever
    from .ai_coordinator.ai_engine import AIEngine
    
    # Import new emotional response services
    from .ai_emotion.greeting_service import GreetingService
    from .ai_emotion.drink_service import DrinkService
    from .ai_emotion.poetic_service import PoeticResponseService
    
    # Import new logic and utility services
    from .ai_logic.context_analysis_service import ContextAnalysisService
    from .utilities.date_conversion_service import DateConversionService
    from .utilities.content_filter_service import ContentFilterService
    from .utilities.text_utility_service import TextUtilityService
    
    # Import new attention and wisdom services
    from .ai_attention.character_tracking_service import CharacterTrackingService
    from .ai_attention.roleplay_exit_service import RoleplayExitService
    from .ai_wisdom.context_coordination_service import ContextCoordinationService
    
    container = get_container()
    
    # Register core services as singletons
    container.register_singleton('roleplay_state', RoleplayStateManager)
    container.register_singleton('db_controller', FleetDatabaseController)
    container.register_singleton('emotion_engine', EmotionEngine)
    container.register_singleton('attention_engine', AttentionEngine)
    container.register_singleton('logic_engine', LogicEngine)
    container.register_singleton('knowledge_engine', KnowledgeEngine)
    container.register_singleton('content_retriever', StructuredContentRetriever)
    container.register_singleton('ai_engine', AIEngine)
    
    # Register emotional response services
    container.register_singleton('greeting_service', GreetingService)
    container.register_singleton('drink_service', DrinkService)
    container.register_singleton('poetic_service', PoeticResponseService)
    
    # Register logic and utility services
    container.register_singleton('context_analysis_service', ContextAnalysisService)
    container.register_singleton('date_conversion_service', DateConversionService)
    container.register_singleton('content_filter_service', ContentFilterService)
    container.register_singleton('text_utility_service', TextUtilityService)
    
    # Register attention and wisdom services
    container.register_singleton('character_tracking_service', CharacterTrackingService)
    container.register_singleton('roleplay_exit_service', RoleplayExitService)
    container.register_singleton('context_coordination_service', ContextCoordinationService)

# Convenience functions for common services
def get_roleplay_state() -> 'RoleplayStateManager':
    """Get the roleplay state manager."""
    return get_container().get('roleplay_state')

def get_db_controller() -> 'FleetDatabaseController':
    """Get the database controller."""
    return get_container().get('db_controller')

def get_emotion_engine() -> 'EmotionEngine':
    """Get the emotion engine."""
    return get_container().get('emotion_engine')

def get_attention_engine() -> 'AttentionEngine':
    """Get the attention engine."""
    return get_container().get('attention_engine')

def get_logic_engine() -> 'LogicEngine':
    """Get the logic engine."""
    return get_container().get('logic_engine')

def get_knowledge_engine() -> 'KnowledgeEngine':
    """Get the knowledge engine."""
    return get_container().get('knowledge_engine')

def get_content_retriever() -> 'StructuredContentRetriever':
    """Get the content retriever."""
    return get_container().get('content_retriever')

def get_ai_engine() -> 'AIEngine':
    """Get the AI engine."""
    return get_container().get('ai_engine')

# Convenience functions for new emotional response services
def get_greeting_service() -> 'GreetingService':
    """Get the greeting service."""
    return get_container().get('greeting_service')

def get_drink_service() -> 'DrinkService':
    """Get the drink service."""
    return get_container().get('drink_service')

def get_poetic_service() -> 'PoeticResponseService':
    """Get the poetic response service."""
    return get_container().get('poetic_service')

# Convenience functions for new logic and utility services
def get_context_analysis_service() -> 'ContextAnalysisService':
    """Get the context analysis service."""
    return get_container().get('context_analysis_service')

def get_date_conversion_service() -> 'DateConversionService':
    """Get the date conversion service."""
    return get_container().get('date_conversion_service')

def get_content_filter_service() -> 'ContentFilterService':
    """Get the content filter service."""
    return get_container().get('content_filter_service')

def get_text_utility_service() -> 'TextUtilityService':
    """Get the text utility service."""
    return get_container().get('text_utility_service')


# Convenience functions for new attention and wisdom services
def get_character_tracking_service() -> 'CharacterTrackingService':
    """Get the character tracking service."""
    return get_container().get('character_tracking_service')

def get_roleplay_exit_service() -> 'RoleplayExitService':
    """Get the roleplay exit service."""
    return get_container().get('roleplay_exit_service')

def get_context_coordination_service() -> 'ContextCoordinationService':
    """Get the context coordination service."""
    return get_container().get('context_coordination_service') 