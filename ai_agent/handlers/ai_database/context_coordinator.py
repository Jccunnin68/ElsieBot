"""
Context Coordinator - Main Database Context Coordination
========================================================

This module contains the main coordination logic for database context
generation, routing different types of queries to appropriate handlers.
"""

from typing import Dict, Any

from .roleplay_contexts import get_roleplay_context
from .database_contexts import (
    get_character_context,
    get_logs_context,
    get_tell_me_about_context,
    get_federation_archives_context,
    get_stardancer_info_context,
    get_ship_logs_context,
    get_general_with_context,
    get_focused_continuation_context
)
from .ooc_handlers import get_ooc_context


def get_context_for_strategy(strategy: Dict[str, Any], user_message: str) -> str:
    """
    Get the appropriate context from the database based on the response strategy.
    Returns a formatted context string for the AI prompt.
    """
    approach = strategy.get('approach')
    
    if approach == 'roleplay_active':
        return get_roleplay_context(strategy, user_message)
    elif approach == 'roleplay_listening':
        return _get_roleplay_listening_context(strategy, user_message)
    elif approach == 'focused_continuation':
        return get_focused_continuation_context(strategy)
    elif approach == 'character':
        return get_character_context(user_message)
    elif approach == 'federation_archives':
        return get_federation_archives_context(user_message)
    elif approach == 'logs':
        return get_logs_context(user_message, strategy)
    elif approach == 'tell_me_about':
        return get_tell_me_about_context(user_message)
    elif approach == 'stardancer_info':
        return get_stardancer_info_context(user_message, strategy)
    elif approach == 'ship_logs':
        return get_ship_logs_context(user_message)
    elif approach == 'ooc':
        return get_ooc_context(user_message)
    elif approach == 'general_with_context':
        return get_general_with_context(user_message)
    
    return ""


def _get_roleplay_listening_context(strategy: Dict[str, Any], user_message: str) -> str:
    """
    Generate context for roleplay listening mode.
    This is handled directly in the handler with predefined responses.
    """
    # This approach is handled directly in ai_handler.py with predefined responses
    # No AI generation needed for listening mode
    return "" 