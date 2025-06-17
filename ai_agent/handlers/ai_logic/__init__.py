"""
AI Logic - Response Decision and Context Analysis
=================================================

This package handles the core logic for determining appropriate responses
and routing user messages to the correct handler based on the new
agentic architecture.
"""

from .response_decision import ResponseDecision
from .response_router import route_message_to_handler
from .roleplay_handler import handle_roleplay_message
from .structured_query_handler import handle_structured_message
from .structured_query_detector import StructuredQueryDetector
from .logic_engine import get_logic_engine
from ..ai_attention import get_roleplay_state, check_dgm_post, handle_dgm_command
from ..ai_attention.attention_engine import get_attention_engine

__all__ = [
    # Core data structures
    'ResponseDecision',

    # Main entry point for routing
    'route_message_to_handler',

    # Specific handlers
    'handle_roleplay_message',
    'handle_structured_message',

    # Agentic components
    'StructuredQueryDetector',
    'get_logic_engine',
    'get_attention_engine',
    
    # State and DGM Handling (from ai_attention)
    'get_roleplay_state',
    'check_dgm_post',
    'handle_dgm_command',
] 