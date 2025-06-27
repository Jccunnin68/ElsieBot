"""
AI Logic - Response Decision and Context Analysis
=================================================

This package handles the core logic for determining appropriate responses
and routing user messages to the correct handler based on the new
agentic architecture.
"""

from .response_decision import ResponseDecision
from .response_router import route_message
from .roleplay_handler import handle_roleplay_message
from .structured_query_handler import handle_structured_message
from .structured_query_detector import StructuredQueryDetector

__all__ = [
    # Core data structures
    'ResponseDecision',

    # Main entry point for routing
    'route_message',

    # Specific handlers
    'handle_roleplay_message',
    'handle_structured_message',

    # Agentic components
    'StructuredQueryDetector',
]

# REMOVED: Global accessor functions moved to service_container
# Use: from handlers.service_container import get_logic_engine, get_attention_engine 