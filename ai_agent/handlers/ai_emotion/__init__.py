"""
AI Emotion - Emotional Context Analysis
=======================================

This package handles the emotional analysis of user messages to provide
contextual information for LLM processing. All responses now go through
the LLM with appropriate emotional context.

Architecture:
- emotion_engine.py: A dedicated LLM-powered engine for emotional analysis
- Service classes: GreetingService, DrinkService, PoeticResponseService (for context)

All services are available through the service container for dependency injection.
Note: These services now provide contextual information rather than generating responses.
"""

# Import service classes for direct access if needed
from .greeting_service import GreetingService
from .drink_service import DrinkService
from .poetic_service import PoeticResponseService

# Import legacy functions for backward compatibility (marked for deprecation)
from .personality_contexts import detect_mock_personality_context

__all__ = [
    # Service Classes (Provide contextual information)
    'GreetingService',
    'DrinkService', 
    'PoeticResponseService',
    
    # Legacy Functions (Deprecated - use service container instead)
    'detect_mock_personality_context',
]

# REMOVED: All old standalone function imports and mocking system
# Use service container: from handlers.service_container import get_*_service 