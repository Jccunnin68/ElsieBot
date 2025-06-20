"""
Service Container - Dependency Injection
========================================

This module provides a service container for managing dependencies and eliminating 
global variables throughout the codebase. It uses dependency injection to provide
clean, testable, and modular code.
"""

from typing import Dict, Any, Optional, Callable, TypeVar, Type
import threading
from contextlib import contextmanager

T = TypeVar('T')

class ServiceContainer:
    """
    A simple dependency injection container that manages service instances
    and eliminates the need for global variables.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
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

def register_default_services():
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
    
    container = get_container()
    
    # Register all services as singletons
    container.register_singleton('roleplay_state', RoleplayStateManager)
    container.register_singleton('db_controller', FleetDatabaseController)
    container.register_singleton('emotion_engine', EmotionEngine)
    container.register_singleton('attention_engine', AttentionEngine)
    container.register_singleton('logic_engine', LogicEngine)
    container.register_singleton('knowledge_engine', KnowledgeEngine)
    container.register_singleton('content_retriever', StructuredContentRetriever)
    container.register_singleton('ai_engine', AIEngine)

# Convenience functions for common services
def get_roleplay_state():
    """Get the roleplay state manager."""
    return get_container().get('roleplay_state')

def get_db_controller():
    """Get the database controller."""
    return get_container().get('db_controller')

def get_emotion_engine():
    """Get the emotion engine."""
    return get_container().get('emotion_engine')

def get_attention_engine():
    """Get the attention engine."""
    return get_container().get('attention_engine')

def get_logic_engine():
    """Get the logic engine."""
    return get_container().get('logic_engine')

def get_knowledge_engine():
    """Get the knowledge engine."""
    return get_container().get('knowledge_engine')

def get_content_retriever():
    """Get the content retriever."""
    return get_container().get('content_retriever')

def get_ai_engine():
    """Get the AI engine."""
    return get_container().get('ai_engine') 