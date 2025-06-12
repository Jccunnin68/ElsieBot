"""
AI Database - Context Generation and Database Access Package
============================================================

This package handles all database access and context generation logic,
extracted from the massive ai_wisdom.py file.

Components:
- context_coordinator.py: Main context coordination (get_context_for_strategy)
- roleplay_contexts.py: Roleplay-specific context generation
- database_contexts.py: Standard database context generators
- ooc_handlers.py: Out-of-character query handlers
- personality_detection.py: Personality context detection

Usage:
    from handlers.ai_database import get_context_for_strategy, handle_ooc_url_request
    
    context = get_context_for_strategy(strategy, user_message)
"""

from .context_coordinator import get_context_for_strategy
from .ooc_handlers import handle_ooc_url_request
from .roleplay_contexts import get_roleplay_context, detect_roleplay_personality_context
from .database_contexts import (
    get_character_context,
    get_logs_context, 
    get_tell_me_about_context,
    get_federation_archives_context,
    get_stardancer_info_context,
    get_ship_logs_context,
    get_general_with_context
)

__all__ = [
    # Main coordination
    'get_context_for_strategy',
    
    # OOC handlers
    'handle_ooc_url_request',
    
    # Roleplay contexts
    'get_roleplay_context',
    'detect_roleplay_personality_context',
    
    # Database contexts
    'get_character_context',
    'get_logs_context',
    'get_tell_me_about_context', 
    'get_federation_archives_context',
    'get_stardancer_info_context',
    'get_ship_logs_context',
    'get_general_with_context'
] 