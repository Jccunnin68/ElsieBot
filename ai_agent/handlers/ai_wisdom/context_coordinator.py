"""
Context Coordinator - Main Database Context Coordination
========================================================

This module contains the main coordination logic for database context
generation, routing between roleplay and non-roleplay context builders.
Enhanced with roleplay state detection for LLM processor integration.
"""

from typing import Dict, Any

from .roleplay_context_builder import get_enhanced_roleplay_context
from .non_roleplay_context_builder import (
    get_character_context,
    get_logs_context,
    get_tell_me_about_context,
    get_federation_archives_context,
    get_stardancer_info_context,
    get_ship_logs_context,
    get_general_with_context,
    get_focused_continuation_context,
    handle_url_request
)

def _detect_roleplay_context(strategy: Dict[str, Any]) -> bool:
    """Detect if we're in a roleplay context for LLM processor integration"""
    approach = strategy.get('approach', '')
    
    # Direct roleplay approaches
    if approach and approach.startswith('roleplay'):
        return True
    
    # Check for roleplay indicators in strategy
    roleplay_indicators = [
        'roleplay', 'character_interaction', 'in_character', 
        'listening_mode', 'character_response'
    ]
    
    for key, value in strategy.items():
        if isinstance(value, str) and any(indicator in value.lower() for indicator in roleplay_indicators):
            return True
    
    # Check for roleplay state from state manager
    try:
        from ..ai_attention.state_manager import get_roleplay_state
        rp_state = get_roleplay_state()
        return rp_state.is_roleplaying
    except:
        pass
    
    return False

def get_context_for_strategy(strategy: Dict[str, Any], user_message: str) -> str:
    """
    Routes the request to the appropriate context builder based on the strategy.
    - Roleplay approaches are handled by the roleplay_context_builder.
    - All other database approaches are handled by the non_roleplay_context_builder.
    Enhanced with roleplay context detection for LLM processor integration.
    """
    approach = strategy.get('approach')
    
    print(f"🎯 CONTEXT COORDINATOR: Routing approach '{approach}'")
    
    # Detect roleplay context for LLM processor
    is_roleplay = _detect_roleplay_context(strategy)
    if is_roleplay:
        print(f"   🎭 ROLEPLAY CONTEXT DETECTED: Enabling character rule processing")
    
    # Route to Roleplay Context Builder
    if approach and approach.startswith('roleplay'):
        print(f"   🎭 ROUTING TO: Roleplay Context Builder")
        return get_enhanced_roleplay_context(strategy, user_message)
    
    # Route to Non-Roleplay Context Builder for specific database queries
    # Pass roleplay context information to content builders
    elif approach == 'character_info':
        print(f"   📚 ROUTING TO: Non-Roleplay Builder (Character Info)")
        return get_character_context(user_message, strategy, is_roleplay=is_roleplay)
    elif approach == 'federation_archives':
        print(f"   📚 ROUTING TO: Non-Roleplay Builder (Federation Archives)")
        return get_federation_archives_context(user_message, is_roleplay=is_roleplay)
    elif approach == 'logs':
        print(f"   📚 ROUTING TO: Non-Roleplay Builder (Logs)")
        return get_logs_context(user_message, strategy, is_roleplay=is_roleplay)
    elif approach == 'tell_me_about':
        print(f"   📚 ROUTING TO: Non-Roleplay Builder (Tell Me About)")
        return get_tell_me_about_context(user_message, is_roleplay=is_roleplay)
    elif approach == 'stardancer_info':
        print(f"   📚 ROUTING TO: Non-Roleplay Builder (Stardancer Info)")
        return get_stardancer_info_context(user_message, strategy, is_roleplay=is_roleplay)
    elif approach == 'ship_logs':
        print(f"   📚 ROUTING TO: Non-Roleplay Builder (Ship Logs)")
        return get_ship_logs_context(user_message, is_roleplay=is_roleplay)
    elif approach == 'url_request':
        print(f"   📚 ROUTING TO: Non-Roleplay Builder (URL Request)")
        return handle_url_request(user_message, is_roleplay=is_roleplay)
    elif approach == 'general_with_context':
        print(f"   📚 ROUTING TO: Non-Roleplay Builder (General)")
        return get_general_with_context(user_message, is_roleplay=is_roleplay)
    elif approach == 'focused_continuation':
        print(f"   📚 ROUTING TO: Non-Roleplay Builder (Focused Continuation)")
        return get_focused_continuation_context(strategy, is_roleplay=is_roleplay)
    
    # Mock approaches or approaches that don't require context
    elif approach and (approach.startswith('mock_') or approach in ['menu_request', 'reset']):
        print(f"   🤖 NO CONTEXT: Mock or menu response for approach '{approach}'")
        return ""
    
    # Fallback for any unknown approach
    print(f"   ❓ UNKNOWN/NO-CONTEXT APPROACH: '{approach}' - no context will be provided.")
    return ""


# _get_roleplay_listening_context removed - now handled in roleplay_handler.py 