"""
AI Mock Response Subsystem
==========================

This package contains all mock response functionality, organized into modular components.
Mock responses are used when the Gemma API is unavailable or for simple conversational interactions.

Components:
- mock_responses.py: Core mock response coordination
- personality_contexts.py: Personality detection for mock responses
- drink_menu.py: Bar and drink-related responses
- greetings.py: Greeting and farewell responses
- poetic_responses.py: Poetic circuit responses

Usage:
    from handlers.ai_emotion import get_mock_response
    
    response = get_mock_response(user_message, context)
"""

from .mock_responses import get_mock_response, should_use_mock_response
from .personality_contexts import detect_mock_personality_context, is_simple_chat
from .drink_menu import handle_drink_request, get_menu_response
from .greetings import handle_greeting, handle_farewell
from .poetic_responses import get_poetic_response, should_trigger_poetic_circuit, get_reset_response, get_simple_continuation_response

__all__ = [
    'get_mock_response',
    'should_use_mock_response',
    'detect_mock_personality_context',
    'is_simple_chat',
    'handle_drink_request',
    'get_menu_response',
    'handle_greeting',
    'handle_farewell',
    'get_poetic_response',
    'should_trigger_poetic_circuit',
    'get_reset_response',
    'get_simple_continuation_response'
] 