"""
Non-Roleplay Handler - Simple Responses and Factual Queries
===========================================================

This module handles ALL responses when Elsie is NOT in roleplay mode.
Provides simple, efficient responses including:
- Basic mock responses for greetings, farewells
- Factual database queries (character info, logs, ship data)
- Simple conversational responses
- NO bar/menu functionality (that belongs to roleplay)
- NO character relationship tracking

CRITICAL: This handler is ONLY called when NOT in roleplay mode.
"""

from typing import Dict, List, Optional

from .response_decision import ResponseDecision
from .query_detection import (
    is_character_query, is_log_query, extract_tell_me_about_subject,
    is_stardancer_query, is_federation_archives_request, 
    extract_ship_log_query, is_ooc_query
)


def handle_non_roleplay_message(user_message: str, conversation_history: List) -> ResponseDecision:
    """
    Handle ALL non-roleplay mode messages with simple, efficient responses.
    
    Non-roleplay mode provides:
    - Simple mock responses for basic interactions
    - Factual database queries (no character relationships)
    - Basic conversational responses
    - NO bar/menu features (roleplay-only)
    - NO character tracking
    
    Args:
        user_message: The user's message
        conversation_history: Previous conversation turns
        
    Returns:
        ResponseDecision with appropriate strategy
    """
    print(f"\n💬 NON-ROLEPLAY HANDLER - Processing standard message")
    
    # Detect query type for routing
    query_type = detect_non_roleplay_query_type(user_message)
    
    print(f"   📋 Query Type: {query_type}")
    
    # Handle simple mock responses first
    if query_type in ['simple_greeting', 'simple_farewell', 'simple_status', 'simple_conversational']:
        return _handle_simple_mock_response(user_message, query_type)
    
    # Handle special non-roleplay cases
    if query_type == 'menu_request':
        return _handle_menu_request()
    
    if query_type == 'reset_request':
        return _handle_reset_request()
    
    # Handle factual database queries
    if query_type in ['character_info', 'logs', 'ship_info', 'tell_me_about', 'federation_archives']:
        return _handle_factual_database_query(user_message, query_type)
    
    # Default: simple conversational response
    return _handle_default_conversational(user_message)


def detect_non_roleplay_query_type(user_message: str) -> str:
    """
    Detect what type of non-roleplay response is needed.
    Focuses on factual queries and simple interactions.
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
    elif is_stardancer_query(user_message):
        return 'ship_info'
    elif is_federation_archives_request(user_message):
        return 'federation_archives'
    elif extract_ship_log_query(user_message)[0]:
        return 'ship_logs'
    elif is_ooc_query(user_message)[0]:
        return 'ooc_query'
    
    # Default
    else:
        return 'general_conversational'


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


def _handle_factual_database_query(user_message: str, query_type: str) -> ResponseDecision:
    """Handle factual database queries that need AI generation."""
    print(f"   📚 FACTUAL DATABASE QUERY: {query_type}")
    
    # Build strategy for database lookup
    strategy = _build_database_strategy(user_message, query_type)
    
    return ResponseDecision(
        needs_ai_generation=True,
        pre_generated_response=None,
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


def _build_database_strategy(user_message: str, query_type: str) -> Dict:
    """Build strategy for database queries."""
    
    # Map query types to database approaches
    approach_mapping = {
        'character_info': 'character_info',
        'logs': 'logs',
        'ship_info': 'stardancer_info',
        'tell_me_about': 'tell_me_about',
        'federation_archives': 'federation_archives',
        'ship_logs': 'ship_logs',
        'ooc_query': 'ooc'
    }
    
    approach = approach_mapping.get(query_type, 'general_with_context')
    
    strategy = {
        'approach': approach,
        'needs_database': True,
        'reasoning': f'Factual database query - {query_type}',
        'context_priority': 'medium'
    }
    
    # Add specific context for certain query types
    if query_type == 'character_info':
        is_character, character_name = is_character_query(user_message)
        if character_name:
            strategy['character_name'] = character_name
    
    elif query_type == 'stardancer_info':
        # Check if asking about command staff
        if any(word in user_message.lower() for word in ['captain', 'commander', 'command', 'staff']):
            strategy['command_query'] = True
    
    return strategy 