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
    SIMPLIFIED context coordinator - routes based on approach type.
    
    The new architecture routes based on mode:
    - Roleplay approaches → use roleplay_contexts.py (EXISTING)
    - Database approaches → use database_contexts.py (EXISTING)
    """
    approach = strategy.get('approach')
    
    print(f"🎯 CONTEXT COORDINATOR: Routing approach '{approach}'")
    
    # Roleplay approaches → use roleplay_contexts.py (EXISTING)
    if approach in ['roleplay_active', 'roleplay_mock_enhanced'] or approach.startswith('roleplay'):
        print(f"   🎭 ROLEPLAY CONTEXT: Using roleplay_contexts.py")
        return get_roleplay_context(strategy, user_message)
    
    # Database approaches → use database_contexts.py (EXISTING)
    elif approach == 'character_info':
        print(f"   📚 DATABASE CONTEXT: Character info")
        return get_character_context(user_message, strategy)
    elif approach == 'federation_archives':
        print(f"   📚 DATABASE CONTEXT: Federation archives")
        return get_federation_archives_context(user_message)
    elif approach == 'logs':
        print(f"   📚 DATABASE CONTEXT: Logs")
        return get_logs_context(user_message, strategy)
    elif approach == 'tell_me_about':
        print(f"   📚 DATABASE CONTEXT: Tell me about")
        return get_tell_me_about_context(user_message)
    elif approach == 'stardancer_info':
        print(f"   📚 DATABASE CONTEXT: Stardancer info")
        return get_stardancer_info_context(user_message, strategy)
    elif approach == 'ship_logs':
        print(f"   📚 DATABASE CONTEXT: Ship logs")
        return get_ship_logs_context(user_message)
    elif approach == 'ooc':
        print(f"   📚 DATABASE CONTEXT: OOC")
        return get_ooc_context(user_message)
    elif approach == 'general_with_context':
        print(f"   📚 DATABASE CONTEXT: General with context")
        return get_general_with_context(user_message)
    elif approach == 'focused_continuation':
        print(f"   📚 DATABASE CONTEXT: Focused continuation")
        return get_focused_continuation_context(strategy)
    
    # Mock approaches don't need context
    elif approach.startswith('mock_') or approach in ['menu_request', 'reset']:
        print(f"   🤖 NO CONTEXT: Mock response '{approach}'")
        return ""
    
    print(f"   ❓ UNKNOWN APPROACH: '{approach}' - no context provided")
    return ""


# _get_roleplay_listening_context removed - now handled in roleplay_handler.py 