"""
Non-Roleplay Handler - Simple Responses and Factual Queries
===========================================================

This module handles ALL responses when Elsie is NOT in roleplay mode.
Provides simple, efficient responses including:
- Basic mock responses for greetings, farewells
- Factual database queries (character info, logs, ship data)
- Comprehensive database responses with disambiguation
- Simple conversational responses
- NO bar/menu functionality (that belongs to roleplay)
- NO character relationship tracking

CRITICAL: This handler is ONLY called when NOT in roleplay mode.
ENHANCED: Comprehensive database responses with summary + disambiguation.
"""

from typing import Dict, List, Optional

from .response_decision import ResponseDecision
from .query_detection import (
    is_character_query, is_log_query, extract_tell_me_about_subject,
    is_stardancer_query, is_federation_archives_request, 
    extract_ship_log_query, extract_url_request, detect_query_type_with_conflicts
)


def handle_non_roleplay_message(user_message: str, conversation_history: List) -> ResponseDecision:
    """
    Handle ALL non-roleplay mode messages with comprehensive responses.
    
    Non-roleplay mode provides:
    - Simple mock responses for basic interactions
    - Comprehensive database queries with disambiguation
    - Basic conversational responses
    - Summary + disambiguation for multiple results
    - NO bar/menu features (roleplay-only)
    - NO character tracking
    
    Args:
        user_message: The user's message
        conversation_history: Previous conversation turns
        
    Returns:
        ResponseDecision with appropriate strategy
    """
    print(f"\n💬 NON-ROLEPLAY HANDLER - Comprehensive response mode")
    
    # Use enhanced query detection with conflict resolution
    query_info = detect_query_type_with_conflicts(user_message)
    
    print(f"   📋 Query Analysis: {query_info['type']} - {query_info.get('subject', 'N/A')}")
    if query_info.get('conflict_resolved'):
        print(f"      ⚖️  Conflict Resolution: {query_info['conflict_resolved']}")
    
    # Handle simple mock responses first
    simple_query_types = ['simple_greeting', 'simple_farewell', 'simple_status', 'simple_conversational']
    if query_info['type'] in simple_query_types:
        return _handle_simple_mock_response(user_message, query_info['type'])
    
    # Handle special non-roleplay cases
    if query_info['type'] == 'menu_request':
        return _handle_menu_request()
    
    if query_info['type'] == 'reset_request':
        return _handle_reset_request()
    
    # Handle comprehensive database queries
    database_query_types = ['character', 'ship', 'ship_log', 'character_log', 'tell_me_about', 'log']
    if query_info['type'] in database_query_types:
        return _handle_comprehensive_database_query(user_message, query_info)
    
    # Handle legacy query detection for compatibility
    legacy_query_type = detect_legacy_query_type(user_message)
    if legacy_query_type in ['character_info', 'logs', 'ship_info', 'federation_archives']:
        return _handle_legacy_database_query(user_message, legacy_query_type)
    
    # Default: simple conversational response
    return _handle_default_conversational(user_message)


def detect_legacy_query_type(user_message: str) -> str:
    """
    Legacy query type detection for compatibility with existing system.
    This maintains compatibility while transitioning to enhanced detection.
    """
    from handlers.ai_emotion.greetings import handle_greeting, handle_farewell, handle_status_inquiry
    from handlers.ai_emotion.drink_menu import is_menu_request
    from handlers.ai_emotion.personality_contexts import is_simple_chat
    
    # Check for simple mock response types
    if handle_greeting(user_message):
        return 'simple_greeting'
    elif handle_farewell(user_message):
        return 'simple_farewell'
    elif handle_status_inquiry(user_message):
        return 'simple_status'
    elif is_simple_chat(user_message):
        return 'simple_conversational'
    
    # Check for special cases
    elif is_menu_request(user_message):
        return 'menu_request'
    elif 'reset' in user_message.lower():
        return 'reset_request'
    
    # Check for factual database queries
    elif is_character_query(user_message)[0]:
        return 'character_info'
    elif is_log_query(user_message):
        return 'logs'
    elif extract_tell_me_about_subject(user_message):
        return 'tell_me_about'
    elif is_federation_archives_request(user_message):
        return 'federation_archives'
    elif extract_ship_log_query(user_message)[0]:
        return 'ship_logs'
    elif extract_url_request(user_message)[0]:
        return 'url_request'
    
    # Default
    else:
        return 'general_conversational'


def _handle_comprehensive_database_query(user_message: str, query_info: Dict) -> ResponseDecision:
    """
    Comprehensive database query for non-roleplay contexts with disambiguation.
    
    KEY FEATURE: Returns summary + disambiguation for multiple results.
    """
    print(f"   📚 COMPREHENSIVE DATABASE QUERY: {query_info['type']}")
    
    strategy = {
        'approach': 'non_roleplay_comprehensive_database',
        'needs_database': True,
        'query_type': query_info['type'],
        'subject': query_info.get('subject'),
        'response_mode': 'comprehensive_with_disambiguation',  # KEY: Comprehensive mode
        'context_priority': 'factual',
        'reasoning': f"Non-roleplay comprehensive database query: {query_info['type']} - {query_info.get('subject', 'N/A')}"
    }
    
    # Add specific query details
    if query_info.get('log_type'):
        strategy['log_type'] = query_info['log_type']
    
    # Add disambiguation requirements for tell_me_about
    if query_info['type'] == 'tell_me_about':
        strategy['needs_title_fallback'] = True
        strategy['provide_disambiguation'] = True
        strategy['include_summary'] = True  # KEY: Summary + disambiguation
        print(f"      📋 Title fallback with disambiguation enabled")
    
    # Add category intersection requirements
    if query_info.get('requires_category_intersection'):
        strategy['valid_categories'] = query_info['valid_categories']
        strategy['requires_category_intersection'] = True
        print(f"      📂 Category intersection required: {query_info['valid_categories']}")
    
    # Add conflict resolution info
    if query_info.get('conflict_resolved'):
        strategy['conflict_info'] = query_info['conflict_resolved']
        print(f"      ⚖️  Conflict resolved: {query_info['conflict_resolved']}")
    
    return ResponseDecision(
        needs_ai_generation=True,
        pre_generated_response=None,
        strategy=strategy
    )


def _handle_legacy_database_query(user_message: str, query_type: str) -> ResponseDecision:
    """Handle legacy database queries for compatibility."""
    print(f"   🔄 LEGACY DATABASE QUERY: {query_type}")
    
    # Build strategy for database lookup
    strategy = _build_legacy_database_strategy(user_message, query_type)
    
    return ResponseDecision(
        needs_ai_generation=True,
        pre_generated_response=None,
        strategy=strategy
    )


def _handle_simple_mock_response(user_message: str, query_type: str) -> ResponseDecision:
    """Handle simple mock responses for basic interactions."""
    from handlers.ai_emotion.mock_responses import get_mock_response
    
    print(f"   🤖 SIMPLE MOCK: {query_type}")
    
    # Get appropriate mock response
    mock_response = get_mock_response(user_message)
    
    strategy = {
        'approach': f'mock_{query_type}',
        'needs_database': False,
        'reasoning': f'Simple mock response for {query_type}',
        'context_priority': 'none'
    }
    
    return ResponseDecision(
        needs_ai_generation=False,
        pre_generated_response=mock_response,
        strategy=strategy
    )


def _handle_menu_request() -> ResponseDecision:
    """Handle menu requests in non-roleplay mode."""
    from handlers.ai_emotion.drink_menu import get_menu_response
    
    print(f"   📋 MENU REQUEST: Non-roleplay menu")
    
    menu_response = get_menu_response()
    
    strategy = {
        'approach': 'menu_request',
        'needs_database': False,
        'reasoning': 'Menu request in non-roleplay mode',
        'context_priority': 'none'
    }
    
    return ResponseDecision(
        needs_ai_generation=False,
        pre_generated_response=menu_response,
        strategy=strategy
    )


def _handle_reset_request() -> ResponseDecision:
    """Handle reset requests."""
    from handlers.ai_emotion import get_reset_response
    
    print(f"   🔄 RESET REQUEST")
    
    reset_response = get_reset_response()
    
    strategy = {
        'approach': 'reset',
        'needs_database': False,
        'reasoning': 'Reset request',
        'context_priority': 'none'
    }
    
    return ResponseDecision(
        needs_ai_generation=False,
        pre_generated_response=reset_response,
        strategy=strategy
    )


def _handle_default_conversational(user_message: str) -> ResponseDecision:
    """Handle default conversational responses."""
    from handlers.ai_emotion.personality_contexts import is_simple_chat
    
    if is_simple_chat(user_message):
        # Simple mock response
        from handlers.ai_emotion.mock_responses import get_mock_response
        mock_response = get_mock_response(user_message)
        
        strategy = {
            'approach': 'simple_conversational',
            'needs_database': False,
            'reasoning': 'Simple conversational response',
            'context_priority': 'none'
        }
        
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=mock_response,
            strategy=strategy
        )
    else:
        # General AI response with light context
        strategy = {
            'approach': 'general_with_context',
            'needs_database': True,
            'reasoning': 'General conversational response with light context',
            'context_priority': 'low'
        }
        
        return ResponseDecision(
            needs_ai_generation=True,
            pre_generated_response=None,
            strategy=strategy
        )


def _build_legacy_database_strategy(user_message: str, query_type: str) -> Dict:
    """Build strategy for legacy database queries."""
    
    # Map query types to database approaches
    approach_mapping = {
        'character_info': 'character_info',
        'logs': 'logs',
        'ship_info': 'ship_info',
        'tell_me_about': 'tell_me_about',
        'federation_archives': 'federation_archives',
        'ship_logs': 'ship_logs',
        'url_request': 'url_request'
    }
    
    approach = approach_mapping.get(query_type, 'general_with_context')
    
    strategy = {
        'approach': approach,
        'needs_database': True,
        'reasoning': f'Legacy database query - {query_type}',
        'context_priority': 'medium'
    }
    
    # Add specific context for certain query types
    if query_type == 'character_info':
        is_character, character_name = is_character_query(user_message)
        if character_name:
            strategy['character_name'] = character_name
    
    elif query_type == 'ship_info':
        # Extract ship name from the message (default to Stardancer if not specified)
        ship_name = "Stardancer"  # Default ship
        # Could add ship name extraction logic here if needed
        strategy['ship_name'] = ship_name
    
    return strategy 